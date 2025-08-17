import uuid
from datetime import datetime
from typing import Optional
from supabase import Client

from app.database.client import get_database_client
from app.schemas.payment_intent import (
    PaymentIntentCreate,
    PaymentIntentResponse,
    PaymentIntentStatus,
    TransactionCompleteUpdate
)


class PaymentIntentService:
    """Service for managing payment intents."""
    
    def __init__(self, db_client: Optional[Client] = None):
        self.db = db_client or get_database_client()
    
    async def create_payment_intent(
        self, 
        payment_data: PaymentIntentCreate
    ) -> PaymentIntentResponse:
        """
        Create a new payment intent.
        
        Args:
            payment_data: Payment intent creation data
            
        Returns:
            PaymentIntentResponse: Created payment intent
            
        Raises:
            ValueError: If validation fails
        """
        # Generate unique intent ID
        intent_id = f"pi_{uuid.uuid4().hex[:12]}"
        
        # Get vendor information
        vendor_result = self.db.table("vendors").select("wallet_address, preferred_dest_chain_id").eq("vendor_id", payment_data.vendor_id).execute()
        
        if not vendor_result.data:
            raise ValueError(f"Vendor not found: {payment_data.vendor_id}")
        
        vendor_data = vendor_result.data[0]
        destination_address = vendor_data["wallet_address"]
        destination_chain_id = vendor_data["preferred_dest_chain_id"]
        
        # Get product information
        product_result = self.db.table("products").select("default_amount_usdc_minor, vendor_id").eq("product_id", payment_data.product_id).execute()
        
        if not product_result.data:
            raise ValueError(f"Product not found: {payment_data.product_id}")
        
        product_data = product_result.data[0]
        
        # Verify product belongs to vendor
        if product_data["vendor_id"] != payment_data.vendor_id:
            raise ValueError(f"Product {payment_data.product_id} does not belong to vendor {payment_data.vendor_id}")
        
        # Get price from product
        price_usdc_minor = product_data["default_amount_usdc_minor"]
        if price_usdc_minor is None:
            raise ValueError(f"Product {payment_data.product_id} has no default price set")
        
        # Create payment intent record
        now = datetime.utcnow()
        payment_intent_data = {
            "intent_id": intent_id,
            "vendor_id": payment_data.vendor_id,
            "product_id": payment_data.product_id,
            "price_usdc_minor": price_usdc_minor,
            "destination_chain_id": destination_chain_id,
            "destination_address": destination_address,
            "status": PaymentIntentStatus.CREATED.value,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        # Insert into database
        result = self.db.table("payment_intents").insert(payment_intent_data).execute()
        
        if not result.data:
            raise Exception("Failed to create payment intent")
        
        created_intent = result.data[0]
        
        # Return response
        return PaymentIntentResponse(
            intent_id=intent_id,
            vendor_id=payment_data.vendor_id,
            product_id=payment_data.product_id,
            status=PaymentIntentStatus.CREATED,
            price_usdc_minor=price_usdc_minor,
            destination_chain_id=destination_chain_id,
            destination_address=destination_address,
            source_chain_id=None,
            source_address=None,
            transaction_hash=None,
            created_at=self._parse_timestamp(created_intent["created_at"]),
            updated_at=self._parse_timestamp(created_intent["updated_at"])
        )
    
    async def get_payment_intent(self, intent_id: str) -> Optional[PaymentIntentResponse]:
        """
        Retrieve a payment intent by ID.
        
        Args:
            intent_id: Payment intent identifier
            
        Returns:
            PaymentIntentResponse or None if not found
        """
        result = self.db.table("payment_intents").select("*").eq("intent_id", intent_id).execute()
        
        if not result.data:
            return None
        
        intent_data = result.data[0]

        return PaymentIntentResponse(
            intent_id=intent_data["intent_id"],
            vendor_id=intent_data["vendor_id"],
            product_id=intent_data["product_id"],
            status=PaymentIntentStatus(intent_data["status"]),
            price_usdc_minor=intent_data["price_usdc_minor"],
            destination_chain_id=intent_data["destination_chain_id"],
            destination_address=intent_data["destination_address"],
            source_chain_id=intent_data.get("source_chain_id"),
            source_address=intent_data.get("source_address"),
            transaction_hash=intent_data.get("transaction_hash"),
            created_at=self._parse_timestamp(intent_data["created_at"]),
            updated_at=self._parse_timestamp(intent_data["updated_at"])
        )
    
    async def complete_transaction(
        self, 
        intent_id: str, 
        transaction_update: TransactionCompleteUpdate
    ) -> Optional[PaymentIntentResponse]:
        """
        Complete a payment intent transaction with full transaction details.
        
        This method handles both successful and failed transactions:
        - If status is 'settled': Payment succeeded, intent is complete
        - If status is 'failed': Payment failed, user can retry with same intent
        
        Args:
            intent_id: Payment intent identifier
            transaction_update: Transaction completion data
            
        Returns:
            Updated PaymentIntentResponse or None if not found
        """
        # Validate that status is either settled or failed
        if transaction_update.payment_status not in [PaymentIntentStatus.SETTLED, PaymentIntentStatus.FAILED]:
            raise ValueError(f"Invalid payment status: {transaction_update.payment_status}. Must be 'settled' or 'failed'")
        
        # Get current payment intent to check current status
        current_intent = await self.get_payment_intent(intent_id)
        if not current_intent:
            return None
        
        # Allow updates from 'created' or 'failed' status (enabling retries)
        if current_intent.status not in [PaymentIntentStatus.CREATED, PaymentIntentStatus.FAILED]:
            raise ValueError(f"Cannot update payment intent with status '{current_intent.status}'. Only 'created' or 'failed' intents can be updated.")
        
        # Update the record
        update_data = {
            "transaction_hash": transaction_update.transaction_hash,
            "source_chain_id": transaction_update.source_chain_id,
            "source_address": transaction_update.source_address,
            "status": transaction_update.payment_status.value,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = self.db.table("payment_intents").update(update_data).eq("intent_id", intent_id).execute()
        
        if not result.data:
            return None
        
        # Return updated intent
        return await self.get_payment_intent(intent_id)
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse Supabase timestamp string to datetime object.
        
        Args:
            timestamp_str: Timestamp string from Supabase
            
        Returns:
            datetime: Parsed datetime object
        """
        # Remove 'Z' and replace with '+00:00' for timezone
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        
        # Handle microseconds precision issues
        if '+' in timestamp_str:
            dt_part, tz_part = timestamp_str.rsplit('+', 1)
            if '.' in dt_part:
                # Limit microseconds to 6 digits
                base_part, microseconds = dt_part.split('.')
                microseconds = microseconds[:6].ljust(6, '0')
                timestamp_str = f"{base_part}.{microseconds}+{tz_part}"
        
        try:
            return datetime.fromisoformat(timestamp_str)
        except ValueError:
            # Fallback: parse without timezone and assume UTC
            base_timestamp = timestamp_str.split('+')[0].split('Z')[0]
            if '.' in base_timestamp:
                base_part, microseconds = base_timestamp.split('.')
                microseconds = microseconds[:6].ljust(6, '0')
                base_timestamp = f"{base_part}.{microseconds}"
            return datetime.fromisoformat(base_timestamp).replace(tzinfo=datetime.now().astimezone().tzinfo)