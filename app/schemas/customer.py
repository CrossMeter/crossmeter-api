from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class CustomerCreate(BaseModel):
    """Schema for creating a new customer."""
    email: EmailStr = Field(..., description="Customer email address")
    name: Optional[str] = Field(None, description="Customer full name")
    metadata: Optional[dict] = Field(None, description="Additional customer metadata")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "alice@example.com",
                "name": "Alice Johnson",
                "metadata": {
                    "source": "web_app",
                    "referral_code": "FRIEND123"
                }
            }
        }
    )


class CustomerResponse(BaseModel):
    """Schema for customer response."""
    customer_id: str = Field(..., description="Unique customer identifier")
    email: EmailStr = Field(..., description="Customer email address")
    name: Optional[str] = Field(None, description="Customer full name")
    metadata: Optional[dict] = Field(None, description="Additional customer metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": "cust_abc123",
                "email": "alice@example.com",
                "name": "Alice Johnson",
                "metadata": {
                    "source": "web_app",
                    "referral_code": "FRIEND123"
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )
