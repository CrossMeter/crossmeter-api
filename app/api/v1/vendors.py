from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import timedelta

from app.schemas.vendor import VendorCreate, VendorResponse, VendorCreateWithWallet
from app.schemas.auth import WalletAuthResponse
from app.schemas.user import VendorStatusResponse
from app.services.vendor_service import VendorService
from app.services.auth_service import AuthService
from app.services.user_service import UserService
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


def get_auth_service() -> AuthService:
    """Dependency to get auth service."""
    return AuthService()


def get_user_service() -> UserService:
    """Dependency to get user service."""
    return UserService()


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


@router.post(
    "/{vendor_id}/regenerate-api-key",
    response_model=Dict[str, str],
    summary="Regenerate API Key",
    description="Generate a new API key for the vendor"
)
async def regenerate_api_key(
    vendor_id: str,
    current_vendor: VendorResponse = Depends(get_current_vendor),
    service: VendorService = Depends(get_vendor_service)
) -> Dict[str, str]:
    """
    Regenerate API key for vendor.
    
    **Auth Required:** Must be the vendor requesting regeneration.
    
    **Returns:** New API key that can be used for client SDK integration.
    """
    try:
        # Check if regenerating own API key
        if current_vendor.vendor_id != vendor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only regenerate your own API key"
            )
            
        new_api_key = await service.regenerate_api_key(vendor_id)
        
        return {"api_key": new_api_key}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate API key: {str(e)}"
        )


@router.get(
    "/wallet/{wallet_address}",
    response_model=VendorStatusResponse,
    summary="Check Vendor Status by Wallet Address",
    description="Check if vendor exists and get vendor status by wallet address"
)
async def check_vendor_status_by_wallet(
    wallet_address: str,
    vendor_service: VendorService = Depends(get_vendor_service)
) -> VendorStatusResponse:
    """
    Check vendor status by wallet address.
    
    This endpoint:
    1. Checks if a user exists with the wallet address
    2. If user exists, checks if they have a vendor profile
    3. Returns vendor data and completion status if vendor exists
    
    **Path Parameters:**
    - `wallet_address`: The Ethereum wallet address (e.g., "0x1234567890123456789012345678901234567890")
    
    **Returns:** Vendor status information including existence and completion status
    """
    try:
        return await vendor_service.get_vendor_status_by_wallet(wallet_address)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check vendor status: {str(e)}"
        )


@router.post(
    "/create-with-wallet",
    response_model=WalletAuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Vendor with Wallet",
    description="Create a new vendor account with wallet authentication and return JWT token"
)
async def create_vendor_with_wallet(
    vendor_data: VendorCreateWithWallet,
    vendor_service: VendorService = Depends(get_vendor_service),
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service)
) -> WalletAuthResponse:
    """
    Create a new vendor account with wallet authentication.
    
    This endpoint:
    1. Validates vendor data including email format and wallet address
    2. Creates a new vendor with a unique vendor_id (no password required)
    3. Links the vendor to the existing user record
    4. Sets up enabled source chains and preferred destination chain
    5. Returns JWT access token and vendor_id
    
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
        # First, get the user by wallet address
        user = await user_service.get_user_by_wallet(vendor_data.wallet_address)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No user found with wallet address {vendor_data.wallet_address}. Please connect wallet first."
            )
        
        # Create vendor linked to the user
        vendor = await vendor_service.create_vendor_with_wallet(vendor_data, user.user_id)
        
        # Create JWT token
        access_token_expires = timedelta(minutes=30)
        access_token = auth_service.create_access_token(
            data={"sub": vendor.vendor_id}, expires_delta=access_token_expires
        )
        
        return WalletAuthResponse(
            access_token=access_token,
            vendor_id=vendor.vendor_id
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create vendor: {str(e)}"
        )
