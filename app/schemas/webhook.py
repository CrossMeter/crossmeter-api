from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class WebhookEventType(str, Enum):
    """Webhook event type enum."""
    PAYMENT_INTENT_CREATED = "payment_intent.created"
    PAYMENT_INTENT_SUBMITTED = "payment_intent.submitted"
    PAYMENT_INTENT_SETTLED = "payment_intent.settled"
    SUBSCRIPTION_RENEWED = "subscription.renewed"


class WebhookPayload(BaseModel):
    """Schema for webhook payload sent to vendors."""
    event_type: WebhookEventType = Field(..., description="Type of webhook event")
    vendor_id: str = Field(..., description="Vendor identifier")
    intent_id: Optional[str] = Field(None, description="Payment intent identifier")
    subscription_id: Optional[str] = Field(None, description="Subscription identifier")
    product_id: str = Field(..., description="Product identifier")
    amount_usdc_minor: int = Field(..., description="Amount in USDC minor units")
    src_chain_id: int = Field(..., description="Source chain ID")
    dest_chain_id: int = Field(..., description="Destination chain ID")
    src_tx_hash: Optional[str] = Field(None, description="Source transaction hash")
    dest_tx_hash: Optional[str] = Field(None, description="Destination transaction hash")
    customer_email: Optional[str] = Field(None, description="Customer email")
    timestamp: datetime = Field(..., description="Event timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional event metadata")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_type": "payment_intent.submitted",
                "vendor_id": "v_123",
                "intent_id": "pi_f83c",
                "subscription_id": None,
                "product_id": "p_abc",
                "amount_usdc_minor": 990000,
                "src_chain_id": 84532,
                "dest_chain_id": 8453,
                "src_tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                "dest_tx_hash": None,
                "customer_email": "alice@example.com",
                "timestamp": "2024-01-01T00:00:00Z",
                "metadata": {
                    "payment_method": "wallet",
                    "user_agent": "Mozilla/5.0..."
                }
            }
        }
    )
