from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class SubscriptionStatus(str, Enum):
    """Subscription status enum."""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class BillingInterval(str, Enum):
    """Billing interval enum."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class SubscriptionCreate(BaseModel):
    """Schema for creating a new subscription."""
    vendor_id: str = Field(..., description="Vendor identifier")
    product_id: str = Field(..., description="Product identifier")
    plan_id: str = Field(..., description="Subscription plan identifier")
    customer_email: str = Field(..., description="Customer email address")
    src_chain_id: int = Field(..., description="Source chain ID (where customer pays from)")
    dest_chain_id: int = Field(..., description="Destination chain ID (where vendor receives)")
    billing_interval: BillingInterval = Field(..., description="Billing interval")
    amount_usdc_minor: int = Field(..., gt=0, description="Amount per billing cycle in USDC minor units")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "vendor_id": "v_123",
                "product_id": "p_abc",
                "plan_id": "plan_monthly_premium",
                "customer_email": "alice@example.com",
                "src_chain_id": 84532,
                "dest_chain_id": 8453,
                "billing_interval": "monthly",
                "amount_usdc_minor": 9990000
            }
        }
    )


class SubscriptionResponse(BaseModel):
    """Schema for subscription response."""
    subscription_id: str = Field(..., description="Unique subscription identifier")
    vendor_id: str = Field(..., description="Vendor identifier")
    product_id: str = Field(..., description="Product identifier")
    plan_id: str = Field(..., description="Subscription plan identifier")
    customer_email: str = Field(..., description="Customer email address")
    status: SubscriptionStatus = Field(..., description="Current subscription status")
    src_chain_id: int = Field(..., description="Source chain ID")
    dest_chain_id: int = Field(..., description="Destination chain ID")
    billing_interval: BillingInterval = Field(..., description="Billing interval")
    amount_usdc_minor: int = Field(..., description="Amount per billing cycle in USDC minor units")
    next_renewal_at: datetime = Field(..., description="Next renewal timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subscription_id": "sub_xyz789",
                "vendor_id": "v_123",
                "product_id": "p_abc",
                "plan_id": "plan_monthly_premium",
                "customer_email": "alice@example.com",
                "status": "active",
                "src_chain_id": 84532,
                "dest_chain_id": 8453,
                "billing_interval": "monthly",
                "amount_usdc_minor": 9990000,
                "next_renewal_at": "2024-02-01T00:00:00Z",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )


class SubscriptionRenewal(BaseModel):
    """Schema for subscription renewal response."""
    subscription_id: str = Field(..., description="Subscription identifier")
    payment_intent: dict = Field(..., description="New payment intent for this renewal cycle")
    next_renewal_at: datetime = Field(..., description="Updated next renewal timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subscription_id": "sub_xyz789",
                "payment_intent": {
                    "intent_id": "pi_renewal_123",
                    "status": "awaiting_user_tx",
                    "router": {
                        "address": "0xROUTER...",
                        "chain_id": 84532,
                        "function": "createPayment",
                        "calldata": "0xabcdef..."
                    }
                },
                "next_renewal_at": "2024-03-01T00:00:00Z"
            }
        }
    )
