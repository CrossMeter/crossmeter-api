from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class ProductType(str, Enum):
    """Product type enum."""
    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"
    USAGE_BASED = "usage_based"


class ProductCreate(BaseModel):
    """Schema for creating a new product."""
    vendor_id: str = Field(..., description="Vendor identifier who owns this product")
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    product_type: ProductType = Field(..., description="Type of product billing")
    default_amount_usdc_minor: Optional[int] = Field(None, gt=0, description="Default amount in USDC minor units")
    metadata: Optional[dict] = Field(None, description="Additional product metadata")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "vendor_id": "v_123",
                "name": "Premium API Access",
                "description": "Monthly access to premium API features",
                "product_type": "subscription",
                "default_amount_usdc_minor": 9990000,
                "metadata": {
                    "features": ["unlimited_requests", "priority_support"],
                    "category": "api_access"
                }
            }
        }
    )


class ProductResponse(BaseModel):
    """Schema for product response."""
    product_id: str = Field(..., description="Unique product identifier")
    vendor_id: str = Field(..., description="Vendor identifier")
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    product_type: ProductType = Field(..., description="Type of product billing")
    default_amount_usdc_minor: Optional[int] = Field(None, description="Default amount in USDC minor units")
    metadata: Optional[dict] = Field(None, description="Additional product metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_id": "p_abc",
                "vendor_id": "v_123",
                "name": "Premium API Access",
                "description": "Monthly access to premium API features",
                "product_type": "subscription",
                "default_amount_usdc_minor": 9990000,
                "metadata": {
                    "features": ["unlimited_requests", "priority_support"],
                    "category": "api_access"
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )
