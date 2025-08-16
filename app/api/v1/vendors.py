from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.schemas.vendor import VendorCreate, VendorResponse
from app.services.vendor_service import VendorService
from .auth import get_current_vendor

router = APIRouter()


class VendorUpdate(BaseModel):
    """Schema for updating vendor information."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Vendor company name")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for payment notifications")
    preferred_dest_chain_id: Optional[int] = Field(None, description="Preferred destination chain ID")
    enabled_source_chains: Optional[list[int]] = Field(None, description="Chain IDs that customers can pay from")
    wallet_address: Optional[str] = Field(None, min_length=42, max_length=42, description="Ethereum wallet address")
    metadata: Optional[dict] = Field(None, description="Additional vendor metadata")


def get_vendor_service() -> VendorService:
    """Dependency to get vendor service."""
    return VendorService()


@router.post(
    "/",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Vendor",
    description="Create a new vendor account"
)
async def create_vendor(
    vendor_data: VendorCreate,
    service: VendorService = Depends(get_vendor_service)
) -> VendorResponse:
    """
    Create a new vendor account.
    
    This endpoint:
    1. Validates vendor data including email format and wallet address
    2. Creates a new vendor with a unique vendor_id
    3. Sets up enabled source chains and preferred destination chain
    4. Returns the complete vendor information
    
    **Example Request:**
    ```json
    {
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
    ```
    """
    try:
        return await service.create_vendor(vendor_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create vendor: {str(e)}"
        )


@router.get(
    "/{vendor_id}",
    response_model=VendorResponse,
    summary="Get Vendor",
    description="Retrieve vendor details by ID"
)
async def get_vendor(
    vendor_id: str,
    current_vendor: VendorResponse = Depends(get_current_vendor),
    service: VendorService = Depends(get_vendor_service)
) -> VendorResponse:
    """
    Retrieve vendor details by vendor ID.
    
    **Auth Required:** Must be the vendor being requested.
    
    **Path Parameters:**
    - `vendor_id`: The unique vendor identifier (e.g., "v_123")
    """
    try:
        # Check if requesting own vendor details
        if current_vendor.vendor_id != vendor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only access your own vendor details"
            )
        return current_vendor
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve vendor: {str(e)}"
        )


@router.patch(
    "/{vendor_id}",
    response_model=VendorResponse,
    summary="Update Vendor",
    description="Update vendor settings and configuration"
)
async def update_vendor(
    vendor_id: str,
    update_data: VendorUpdate,
    current_vendor: VendorResponse = Depends(get_current_vendor),
    service: VendorService = Depends(get_vendor_service)
) -> VendorResponse:
    """
    Update vendor settings and configuration.
    
    **Auth Required:** Must be the vendor being updated.
    
    **Path Parameters:**
    - `vendor_id`: The unique vendor identifier (e.g., "v_123")
    """
    try:
        # Check if updating own vendor details
        if current_vendor.vendor_id != vendor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only update your own vendor details"
            )
            
        # Convert Pydantic model to dict, excluding None values
        update_dict = update_data.model_dump(exclude_none=True)
        
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields provided for update"
            )
        
        updated_vendor = await service.update_vendor(vendor_id, update_dict)
        if not updated_vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vendor {vendor_id} not found"
            )
        
        return updated_vendor
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update vendor: {str(e)}"
        )
