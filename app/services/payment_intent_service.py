import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from supabase import Client

from app.database.client import get_database_client
from app.schemas.payment_intent import (
    PaymentIntentCreate,
    PaymentIntentResponse,
    PaymentIntentStatus,
    RouterInfo,
    TransactionHashUpdate
)
from app.schemas.webhook import WebhookEventType
from app.services.router_service import RouterService
from app.services.webhook_service import send_payment_intent_webhook


class PaymentIntentService:
    """Service for managing payment intents."""
    
    def __init__(self, db_client: Optional[Client] = None):
        self.db = db_client or get_database_client()
        self.router_service = RouterService()
    
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
        # Validate chain support
        if not self.router_service.validate_chain_support(
            payment_data.src_chain_id, 
            payment_data.dest_chain_id
        ):
            raise ValueError(f"Unsupported chain combination: {payment_data.src_chain_id} -> {payment_data.dest_chain_id}")
        
        # Generate unique intent ID
        intent_id = f"pi_{uuid.uuid4().hex[:12]}"
        
        # Get vendor information to generate calldata
        vendor_result = self.db.table("vendors").select("wallet_address, preferred_dest_chain_id, enabled_source_chains").eq("vendor_id", payment_data.vendor_id).execute()
        
        if not vendor_result.data:
            raise ValueError(f"Vendor not found: {payment_data.vendor_id}")
        
        vendor_data = vendor_result.data[0]
        vendor_wallet = vendor_data["wallet_address"]
        enabled_source_chains = vendor_data.get("enabled_source_chains", [])
        
        # Validate that the source chain is enabled for this vendor
        if payment_data.src_chain_id not in enabled_source_chains:
            raise ValueError(f"Source chain {payment_data.src_chain_id} is not enabled for vendor {payment_data.vendor_id}")
        
        # Validate that chains are supported by our router
        if not self.router_service.validate_chain_support(payment_data.src_chain_id, payment_data.dest_chain_id):
            raise ValueError(f"Chain combination not supported: {payment_data.src_chain_id} -> {payment_data.dest_chain_id}")
        
        # Generate router calldata
        router_info = self.router_service.generate_payment_calldata(
            vendor_wallet=vendor_wallet,
            amount_usdc_minor=payment_data.amount_usdc_minor,
            src_chain_id=payment_data.src_chain_id,
            dest_chain_id=payment_data.dest_chain_id,
            payment_intent_id=intent_id
        )
        
        # Handle customer creation/retrieval
        customer_id = None
        if payment_data.customer_email:
            customer_id = await self._get_or_create_customer(payment_data.customer_email)
        
        # Create payment intent record
        now = datetime.utcnow()
        payment_intent_data = {
            "intent_id": intent_id,
            "vendor_id": payment_data.vendor_id,
            "product_id": payment_data.product_id,
            "customer_id": customer_id,
            "customer_email": payment_data.customer_email,
            "src_chain_id": payment_data.src_chain_id,
            "dest_chain_id": payment_data.dest_chain_id,
            "amount_usdc_minor": payment_data.amount_usdc_minor,
            "status": PaymentIntentStatus.CREATED.value,  # Initially created, then immediately moved to awaiting_user_tx
            "router_address": router_info["address"],
            "router_function": router_info["function"],
            "calldata_hex": router_info["calldata"],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        # Insert into database
        result = self.db.table("payment_intents").insert(payment_intent_data).execute()
        
        if not result.data:
            raise Exception("Failed to create payment intent")
        
        created_intent = result.data[0]
        
        # Immediately update status to awaiting_user_tx since we're returning calldata to client
        update_result = self.db.table("payment_intents").update({
            "status": PaymentIntentStatus.AWAITING_USER_TX.value,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("intent_id", intent_id).execute()
        
        if update_result.data:
            created_intent = update_result.data[0]
        
        # Send webhook for payment intent creation
        try:
            await send_payment_intent_webhook(
                vendor_id=payment_data.vendor_id,
                event_type=WebhookEventType.PAYMENT_INTENT_CREATED,
                intent_id=intent_id,
                product_id=payment_data.product_id,
                amount_usdc_minor=payment_data.amount_usdc_minor,
                src_chain_id=payment_data.src_chain_id,
                dest_chain_id=payment_data.dest_chain_id,
                customer_email=payment_data.customer_email
            )
        except Exception as e:
            # Log webhook error but don't fail the payment intent creation
            print(f"Warning: Failed to send payment_intent.created webhook: {e}")
        
        # Return response
        return PaymentIntentResponse(
            intent_id=intent_id,
            vendor_id=payment_data.vendor_id,
            product_id=payment_data.product_id,
            status=PaymentIntentStatus.AWAITING_USER_TX,
            src_chain_id=payment_data.src_chain_id,
            dest_chain_id=payment_data.dest_chain_id,
            amount_usdc_minor=payment_data.amount_usdc_minor,
            customer_email=payment_data.customer_email,
            src_tx_hash=None,
            dest_tx_hash=None,
            router=RouterInfo(
                address=router_info["address"],
                chain_id=router_info["chain_id"],
                function=router_info["function"],
                calldata=router_info["calldata"],
                gas_limit=router_info.get("gas_limit"),
                bridge_fee=router_info.get("bridge_fee"),
                estimated_cost=router_info.get("estimated_cost")
            ),
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
            src_chain_id=intent_data["src_chain_id"],
            dest_chain_id=intent_data["dest_chain_id"],
            amount_usdc_minor=intent_data["amount_usdc_minor"],
            customer_email=intent_data["customer_email"],
            src_tx_hash=intent_data["src_tx_hash"],
            dest_tx_hash=intent_data["dest_tx_hash"],
            router=RouterInfo(
                address=intent_data["router_address"],
                chain_id=intent_data["src_chain_id"],
                function=intent_data["router_function"],
                calldata=intent_data["calldata_hex"],
                gas_limit=None,  # Not stored in DB, would need to recalculate
                bridge_fee=None,
                estimated_cost=None
            ),
            created_at=self._parse_timestamp(intent_data["created_at"]),
            updated_at=self._parse_timestamp(intent_data["updated_at"])
        )
    
    async def update_source_transaction(
        self, 
        intent_id: str, 
        tx_update: TransactionHashUpdate
    ) -> Optional[PaymentIntentResponse]:
        """
        Update payment intent with source transaction hash.
        
        Args:
            intent_id: Payment intent identifier
            tx_update: Transaction hash update data
            
        Returns:
            Updated PaymentIntentResponse or None if not found
        """
        # Update the record
        update_data = {
            "src_tx_hash": tx_update.tx_hash,
            "status": PaymentIntentStatus.SUBMITTED.value,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = self.db.table("payment_intents").update(update_data).eq("intent_id", intent_id).execute()
        
        if not result.data:
            return None
        
        # Send webhook for source transaction submission
        updated_intent = await self.get_payment_intent(intent_id)
        if updated_intent:
            try:
                await send_payment_intent_webhook(
                    vendor_id=updated_intent.vendor_id,
                    event_type=WebhookEventType.PAYMENT_INTENT_SUBMITTED,
                    intent_id=intent_id,
                    product_id=updated_intent.product_id,
                    amount_usdc_minor=updated_intent.amount_usdc_minor,
                    src_chain_id=updated_intent.src_chain_id,
                    dest_chain_id=updated_intent.dest_chain_id,
                    src_tx_hash=tx_update.tx_hash,
                    customer_email=updated_intent.customer_email
                )
            except Exception as e:
                print(f"Warning: Failed to send payment_intent.submitted webhook: {e}")
        
        # Return updated intent
        return updated_intent
    
    async def update_destination_transaction(
        self, 
        intent_id: str, 
        tx_update: TransactionHashUpdate
    ) -> Optional[PaymentIntentResponse]:
        """
        Update payment intent with destination transaction hash.
        
        Args:
            intent_id: Payment intent identifier
            tx_update: Transaction hash update data
            
        Returns:
            Updated PaymentIntentResponse or None if not found
        """
        # Update the record
        update_data = {
            "dest_tx_hash": tx_update.tx_hash,
            "status": PaymentIntentStatus.SETTLED.value,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = self.db.table("payment_intents").update(update_data).eq("intent_id", intent_id).execute()
        
        if not result.data:
            return None
        
        # Send webhook for destination transaction settlement
        updated_intent = await self.get_payment_intent(intent_id)
        if updated_intent:
            try:
                await send_payment_intent_webhook(
                    vendor_id=updated_intent.vendor_id,
                    event_type=WebhookEventType.PAYMENT_INTENT_SETTLED,
                    intent_id=intent_id,
                    product_id=updated_intent.product_id,
                    amount_usdc_minor=updated_intent.amount_usdc_minor,
                    src_chain_id=updated_intent.src_chain_id,
                    dest_chain_id=updated_intent.dest_chain_id,
                    src_tx_hash=updated_intent.src_tx_hash,
                    dest_tx_hash=tx_update.tx_hash,
                    customer_email=updated_intent.customer_email
                )
            except Exception as e:
                print(f"Warning: Failed to send payment_intent.settled webhook: {e}")
        
        # Return updated intent
        return updated_intent
    
    async def _get_or_create_customer(self, email: str) -> str:
        """
        Get existing customer or create new one.
        
        Args:
            email: Customer email
            
        Returns:
            str: Customer ID
        """
        # Try to find existing customer
        result = self.db.table("customers").select("customer_id").eq("email", email).execute()
        
        if result.data:
            return result.data[0]["customer_id"]
        
        # Create new customer
        customer_id = f"cust_{uuid.uuid4().hex[:12]}"
        customer_data = {
            "customer_id": customer_id,
            "email": email,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        create_result = self.db.table("customers").insert(customer_data).execute()
        
        if not create_result.data:
            raise Exception("Failed to create customer")
        
        return customer_id
    
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
