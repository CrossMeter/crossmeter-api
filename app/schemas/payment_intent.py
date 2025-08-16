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
    src_chain_id: int = Field(..., description="Source chain ID (where customer pays from)")
    dest_chain_id: int = Field(..., description="Destination chain ID (where vendor receives)")
    amount_usdc_minor: int = Field(..., gt=0, description="Amount in USDC minor units (1 USDC = 1,000,000 minor units)")
    customer_email: Optional[str] = Field(None, description="Optional customer email")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "vendor_id": "v_123",
                "product_id": "p_abc", 
                "src_chain_id": 84532,
                "dest_chain_id": 8453,
                "amount_usdc_minor": 990000,
                "customer_email": "alice@example.com"
            }
        }
    )


class PaymentIntentResponse(BaseModel):
    """Schema for payment intent response."""
    intent_id: str = Field(..., description="Unique payment intent identifier")
    vendor_id: str = Field(..., description="Vendor identifier")
    product_id: str = Field(..., description="Product identifier")
    status: PaymentIntentStatus = Field(..., description="Current payment intent status")
    src_chain_id: int = Field(..., description="Source chain ID")
    dest_chain_id: int = Field(..., description="Destination chain ID")
    amount_usdc_minor: int = Field(..., description="Amount in USDC minor units")
    customer_email: Optional[str] = Field(None, description="Customer email if provided")
    src_tx_hash: Optional[str] = Field(None, description="Source chain transaction hash")
    dest_tx_hash: Optional[str] = Field(None, description="Destination chain transaction hash")
    router: RouterInfo = Field(..., description="Router contract information")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "intent_id": "pi_f83c",
                "vendor_id": "v_123",
                "product_id": "p_abc",
                "status": "awaiting_user_tx",
                "src_chain_id": 84532,
                "dest_chain_id": 8453,
                "amount_usdc_minor": 990000,
                "customer_email": "alice@example.com",
                "src_tx_hash": None,
                "dest_tx_hash": None,
                "router": {
                    "address": "0xROUTER...",
                    "chain_id": 84532,
                    "function": "createPayment",
                    "calldata": "0xabcdef..."
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )


class TransactionHashUpdate(BaseModel):
    """Schema for updating transaction hash."""
    tx_hash: str = Field(..., min_length=66, max_length=66, description="Transaction hash (0x prefixed)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            }
        }
    )


class PaymentIntentUpdate(BaseModel):
    """Schema for internal payment intent updates."""
    status: Optional[PaymentIntentStatus] = None
    src_tx_hash: Optional[str] = None
    dest_tx_hash: Optional[str] = None
