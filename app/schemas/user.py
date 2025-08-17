from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    wallet_address: str = Field(..., min_length=42, max_length=42, description="Ethereum wallet address")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "wallet_address": "0x1234567890123456789012345678901234567890"
            }
        }
    )


class UserResponse(BaseModel):
    """Schema for user response."""
    user_id: str = Field(..., description="Unique user identifier")
    wallet_address: str = Field(..., description="Ethereum wallet address")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "wallet_address": "0x1234567890123456789012345678901234567890",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )


class VendorStatusResponse(BaseModel):
    """Schema for vendor status check response."""
    exists: bool = Field(..., description="Whether vendor exists")
    vendor: Optional[dict] = Field(None, description="Vendor data if exists")
    isComplete: bool = Field(..., description="Whether vendor profile is complete")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exists": True,
                "vendor": {
                    "vendor_id": "v_123",
                    "name": "Acme Corp",
                    "email": "payments@acme.com",
                    "wallet_address": "0x1234567890123456789012345678901234567890",
                    "webhook_url": "https://api.acme.com/webhooks/piaas",
                    "preferred_dest_chain_id": 8453,
                    "enabled_source_chains": [1, 8453, 84532, 10, 42161, 137],
                    "metadata": {
                        "description": "E-commerce platform",
                        "website": "https://acme.com"
                    }
                },
                "isComplete": True
            }
        }
    )

