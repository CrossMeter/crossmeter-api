import uuid
from datetime import datetime, timedelta
from typing import Optional
from supabase import Client

from app.database.client import get_database_client
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionStatus,
    BillingInterval
)
from app.schemas.payment_intent import PaymentIntentCreate, PaymentIntentResponse
from app.schemas.webhook import WebhookEventType
from app.services.payment_intent_service import PaymentIntentService
from app.services.webhook_service import send_subscription_webhook


class SubscriptionService:
    """Service for managing subscriptions."""
    
    def __init__(self, db_client: Optional[Client] = None):
        self.db = db_client or get_database_client()
        self.payment_intent_service = PaymentIntentService(db_client)
    
    async def create_subscription(
        self, 
        subscription_data: SubscriptionCreate
    ) -> SubscriptionResponse:
        """
        Create a new subscription.
        
        Args:
            subscription_data: Subscription creation data
            
        Returns:
            SubscriptionResponse: Created subscription
            
        Raises:
            ValueError: If validation fails
        """
        # Validate vendor exists
        vendor_result = self.db.table("vendors").select("vendor_id").eq("vendor_id", subscription_data.vendor_id).execute()
        if not vendor_result.data:
            raise ValueError(f"Vendor not found: {subscription_data.vendor_id}")
        
        # Validate product exists
        product_result = self.db.table("products").select("product_id").eq("product_id", subscription_data.product_id).execute()
        if not product_result.data:
            raise ValueError(f"Product not found: {subscription_data.product_id}")
        
        # Generate unique subscription ID
        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
        
        # Calculate next renewal date based on billing interval
        next_renewal_at = self._calculate_next_renewal(subscription_data.billing_interval)
        
        # Handle customer creation/retrieval
        customer_id = await self._get_or_create_customer(subscription_data.customer_email)
        
        # Create subscription record
        now = datetime.utcnow()
        subscription_db_data = {
            "subscription_id": subscription_id,
            "vendor_id": subscription_data.vendor_id,
            "product_id": subscription_data.product_id,
            "plan_id": subscription_data.plan_id,
            "customer_email": subscription_data.customer_email,
            "customer_id": customer_id,
            "status": SubscriptionStatus.ACTIVE.value,
            "src_chain_id": subscription_data.src_chain_id,
            "dest_chain_id": subscription_data.dest_chain_id,
            "billing_interval": subscription_data.billing_interval.value,
            "amount_usdc_minor": subscription_data.amount_usdc_minor,
            "next_renewal_at": next_renewal_at.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        # Insert into database
        result = self.db.table("subscriptions").insert(subscription_db_data).execute()
        
        if not result.data:
            raise Exception("Failed to create subscription")
        
        created_subscription = result.data[0]
        
        # Return response
        return SubscriptionResponse(
            subscription_id=subscription_id,
            vendor_id=subscription_data.vendor_id,
            product_id=subscription_data.product_id,
            plan_id=subscription_data.plan_id,
            customer_email=subscription_data.customer_email,
            status=SubscriptionStatus.ACTIVE,
            src_chain_id=subscription_data.src_chain_id,
            dest_chain_id=subscription_data.dest_chain_id,
            billing_interval=subscription_data.billing_interval,
            amount_usdc_minor=subscription_data.amount_usdc_minor,
            next_renewal_at=self._parse_timestamp(created_subscription["next_renewal_at"]),
            created_at=self._parse_timestamp(created_subscription["created_at"]),
            updated_at=self._parse_timestamp(created_subscription["updated_at"])
        )
    
    async def get_subscription(self, subscription_id: str) -> Optional[SubscriptionResponse]:
        """
        Retrieve a subscription by ID.
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            SubscriptionResponse or None if not found
        """
        result = self.db.table("subscriptions").select("*").eq("subscription_id", subscription_id).execute()
        
        if not result.data:
            return None
        
        sub_data = result.data[0]
        
        return SubscriptionResponse(
            subscription_id=sub_data["subscription_id"],
            vendor_id=sub_data["vendor_id"],
            product_id=sub_data["product_id"],
            plan_id=sub_data["plan_id"],
            customer_email=sub_data["customer_email"],
            status=SubscriptionStatus(sub_data["status"]),
            src_chain_id=sub_data["src_chain_id"],
            dest_chain_id=sub_data["dest_chain_id"],
            billing_interval=BillingInterval(sub_data["billing_interval"]),
            amount_usdc_minor=sub_data["amount_usdc_minor"],
            next_renewal_at=self._parse_timestamp(sub_data["next_renewal_at"]),
            created_at=self._parse_timestamp(sub_data["created_at"]),
            updated_at=self._parse_timestamp(sub_data["updated_at"])
        )
    
    async def renew_subscription(self, subscription_id: str) -> dict:
        """
        Create a new payment intent for subscription renewal.
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            dict: Renewal response with payment intent and updated next renewal date
            
        Raises:
            ValueError: If subscription not found or not active
        """
        # Get subscription
        subscription = await self.get_subscription(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")
        
        if subscription.status != SubscriptionStatus.ACTIVE:
            raise ValueError(f"Subscription is not active: {subscription.status}")
        
        # Create payment intent for this renewal
        payment_intent_data = PaymentIntentCreate(
            vendor_id=subscription.vendor_id,
            product_id=subscription.product_id,
            src_chain_id=subscription.src_chain_id,
            dest_chain_id=subscription.dest_chain_id,
            amount_usdc_minor=subscription.amount_usdc_minor,
            customer_email=subscription.customer_email
        )
        
        payment_intent = await self.payment_intent_service.create_payment_intent(payment_intent_data)
        
        # Calculate new next renewal date
        new_next_renewal = self._calculate_next_renewal(subscription.billing_interval)
        
        # Update subscription with new renewal date
        update_data = {
            "next_renewal_at": new_next_renewal.isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        update_result = self.db.table("subscriptions").update(update_data).eq("subscription_id", subscription_id).execute()
        
        if not update_result.data:
            raise Exception("Failed to update subscription renewal date")
        
        # Send webhook for subscription renewal
        try:
            await send_subscription_webhook(
                vendor_id=subscription.vendor_id,
                event_type=WebhookEventType.SUBSCRIPTION_RENEWED,
                subscription_id=subscription_id,
                product_id=subscription.product_id,
                amount_usdc_minor=subscription.amount_usdc_minor,
                intent_id=payment_intent.intent_id,
                src_chain_id=subscription.src_chain_id,
                dest_chain_id=subscription.dest_chain_id,
                customer_email=subscription.customer_email
            )
        except Exception as e:
            print(f"Warning: Failed to send subscription.renewed webhook: {e}")
        
        # Return renewal response
        return {
            "subscription_id": subscription_id,
            "payment_intent": {
                "intent_id": payment_intent.intent_id,
                "status": payment_intent.status,
                "amount_usdc_minor": payment_intent.amount_usdc_minor,
                "router": {
                    "address": payment_intent.router.address,
                    "chain_id": payment_intent.router.chain_id,
                    "function": payment_intent.router.function,
                    "calldata": payment_intent.router.calldata
                }
            },
            "next_renewal_at": new_next_renewal.isoformat()
        }
    
    async def update_subscription_status(
        self, 
        subscription_id: str, 
        status: SubscriptionStatus
    ) -> Optional[SubscriptionResponse]:
        """
        Update subscription status.
        
        Args:
            subscription_id: Subscription identifier
            status: New subscription status
            
        Returns:
            Updated SubscriptionResponse or None if not found
        """
        update_data = {
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = self.db.table("subscriptions").update(update_data).eq("subscription_id", subscription_id).execute()
        
        if not result.data:
            return None
        
        # Return updated subscription
        return await self.get_subscription(subscription_id)
    
    def _calculate_next_renewal(self, billing_interval: BillingInterval) -> datetime:
        """
        Calculate the next renewal date based on billing interval.
        
        Args:
            billing_interval: Billing interval enum
            
        Returns:
            datetime: Next renewal date
        """
        now = datetime.utcnow()
        
        if billing_interval == BillingInterval.MONTHLY:
            return now + timedelta(days=30)
        elif billing_interval == BillingInterval.QUARTERLY:
            return now + timedelta(days=90)
        elif billing_interval == BillingInterval.YEARLY:
            return now + timedelta(days=365)
        else:
            raise ValueError(f"Unsupported billing interval: {billing_interval}")
    
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
        Same logic as PaymentIntentService.
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
