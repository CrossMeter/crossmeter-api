from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class PaymentIntentStatus(str, Enum):
    """Payment intent status enum."""
    CREATED = "created"
    AWAITING_USER_TX = "awaiting_user_tx"
    SUBMITTED = "submitted"
    SETTLED = "settled"


class RouterInfo(BaseModel):
    """Router contract information for transaction execution."""
    address: str = Field(..., description="Router contract address")
    chain_id: int = Field(..., description="Source chain ID where transaction should be executed")
    function: str = Field(..., description="Router function name to call")
    calldata: str = Field(..., description="Hex-encoded calldata for the transaction")
    gas_limit: Optional[int] = Field(None, description="Estimated gas limit for the transaction")
    bridge_fee: Optional[int] = Field(None, description="Bridge fee in USDC minor units (if cross-chain)")
    estimated_cost: Optional[Dict[str, Any]] = Field(None, description="Estimated cost breakdown")


class PaymentIntentCreate(BaseModel):
    """Schema for creating a new payment intent."""
    vendor_id: str = Field(..., description="Vendor identifier")
    product_id: str = Field(..., description="Product identifier") 
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "vendor_id": "v_123",
                "product_id": "p_abc"
            }
        }
    )


class PaymentIntentResponse(BaseModel):
    """Schema for payment intent response."""
    intent_id: str = Field(..., description="Unique payment intent identifier")
    vendor_id: str = Field(..., description="Vendor identifier")
    product_id: str = Field(..., description="Product identifier")
    status: PaymentIntentStatus = Field(..., description="Current payment intent status")
    price_usdc_minor: int = Field(..., description="Price to be paid in USDC minor units")
    destination_chain_id: int = Field(..., description="Destination chain ID where vendor receives payment")
    destination_address: str = Field(..., description="Destination address where vendor receives payment")
    source_chain_id: Optional[int] = Field(None, description="Source chain ID (set when transaction is completed)")
    source_address: Optional[str] = Field(None, description="Source address (set when transaction is completed)")
    transaction_hash: Optional[str] = Field(None, description="Transaction hash (set when transaction is completed)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "intent_id": "pi_f83c",
                "vendor_id": "v_123",
                "product_id": "p_abc",
                "status": "created",
                "price_usdc_minor": 990000,
                "destination_chain_id": 8453,
                "destination_address": "0x742d35Cc6635C0532925a3b8D19dac9dd9bf1234",
                "source_chain_id": None,
                "source_address": None,
                "transaction_hash": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )


class TransactionCompleteUpdate(BaseModel):
    """Schema for completing a payment intent transaction."""
    transaction_hash: str = Field(..., min_length=66, max_length=66, description="Transaction hash (0x prefixed)")
    payment_status: PaymentIntentStatus = Field(..., description="Payment status (submitted or settled)")
    source_chain_id: int = Field(..., description="Source chain ID where payment was made")
    source_address: str = Field(..., min_length=42, max_length=42, description="Source address that made the payment (0x prefixed)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "transaction_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                "payment_status": "settled",
                "source_chain_id": 84532,
                "source_address": "0x742d35Cc6635C0532925a3b8D19dac9dd9bf9876"
            }
        }
    )


class PaymentIntentUpdate(BaseModel):
    """Schema for internal payment intent updates."""
    status: Optional[PaymentIntentStatus] = None
    src_tx_hash: Optional[str] = None
    dest_tx_hash: Optional[str] = None
