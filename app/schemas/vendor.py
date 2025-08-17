from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class VendorCreate(BaseModel):
    """Schema for creating a new vendor."""
    name: str = Field(..., min_length=1, max_length=255, description="Vendor company name")
    email: EmailStr = Field(..., description="Vendor contact email")
    password: str = Field(..., min_length=8, description="Password for vendor login")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for payment notifications")
    preferred_dest_chain_id: int = Field(..., description="Preferred destination chain ID for receiving payments")
    enabled_source_chains: List[int] = Field(default=[1, 8453, 84532, 10, 42161, 137], description="Chain IDs that customers can pay from")
    wallet_address: str = Field(..., min_length=42, max_length=42, description="Ethereum wallet address for receiving payments")
    metadata: Optional[dict] = Field(None, description="Additional vendor metadata")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Acme Corp",
                "email": "payments@acme.com",
                "webhook_url": "https://api.acme.com/webhooks/piaas",
                "preferred_dest_chain_id": 8453,
                "enabled_source_chains": [1, 8453, 84532, 10, 42161, 137],
                "wallet_address": "0x1234567890123456789012345678901234567890",
                "metadata": {
                    "industry": "e-commerce",
                    "plan": "premium"
                }
            }
        }
    )


class VendorCreateWithWallet(BaseModel):
    """Schema for creating a new vendor with wallet authentication (no password)."""
    name: str = Field(..., min_length=1, max_length=255, description="Vendor company name")
    email: EmailStr = Field(..., description="Vendor contact email")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for payment notifications")
    preferred_dest_chain_id: int = Field(..., description="Preferred destination chain ID for receiving payments")
    enabled_source_chains: List[int] = Field(default=[1, 8453, 84532, 10, 42161, 137], description="Chain IDs that customers can pay from")
    wallet_address: str = Field(..., min_length=42, max_length=42, description="Ethereum wallet address for receiving payments")
    metadata: Optional[dict] = Field(None, description="Additional vendor metadata")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Acme Corp",
                "email": "payments@acme.com",
                "webhook_url": "https://api.acme.com/webhooks/piaas",
                "preferred_dest_chain_id": 8453,
                "enabled_source_chains": [1, 8453, 84532, 10, 42161, 137],
                "wallet_address": "0x1234567890123456789012345678901234567890",
                "metadata": {
                    "industry": "e-commerce",
                    "plan": "premium"
                }
            }
        }
    )


class VendorResponse(BaseModel):
    """Schema for vendor response."""
    vendor_id: str = Field(..., description="Unique vendor identifier")
    name: str = Field(..., description="Vendor company name")
    email: EmailStr = Field(..., description="Vendor contact email")
    api_key: Optional[str] = Field(None, description="API key for client SDK integration")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for payment notifications")
    preferred_dest_chain_id: int = Field(..., description="Preferred destination chain ID")
    enabled_source_chains: List[int] = Field(..., description="Chain IDs that customers can pay from")
    wallet_address: str = Field(..., description="Ethereum wallet address")
    metadata: Optional[dict] = Field(None, description="Additional vendor metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "vendor_id": "v_123",
                "name": "Acme Corp",
                "email": "payments@acme.com",
                "webhook_url": "https://api.acme.com/webhooks/piaas",
                "preferred_dest_chain_id": 8453,
                "enabled_source_chains": [1, 8453, 84532, 10, 42161, 137],
                "wallet_address": "0x1234567890123456789012345678901234567890",
                "metadata": {
                    "industry": "e-commerce",
                    "plan": "premium"
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )
