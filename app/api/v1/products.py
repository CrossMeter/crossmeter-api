from fastapi import APIRouter, HTTPException, Depends, status, Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from app.schemas.product import ProductCreate, ProductResponse, ProductType
from app.services.product_service import ProductService
from .auth import get_current_vendor

router = APIRouter()


class ProductUpdate(BaseModel):
    """Schema for updating product information."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    product_type: Optional[ProductType] = Field(None, description="Type of product billing")
    default_amount_usdc_minor: Optional[int] = Field(None, gt=0, description="Default amount in USDC minor units")
    metadata: Optional[dict] = Field(None, description="Additional product metadata")


def get_product_service() -> ProductService:
    """Dependency to get product service."""
    return ProductService()


@router.post(
    "/{vendor_id}/products/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Product",
    description="Create a new product for a vendor"
)
async def create_product(
    vendor_id: str = Path(..., description="Vendor ID"),
    product_data: ProductCreate = ...,
    current_vendor = Depends(get_current_vendor),
    service: ProductService = Depends(get_product_service)
) -> ProductResponse:
    """
    Create a new product for a vendor.
    
    This endpoint:
    1. Validates that the vendor exists
    2. Creates a new product with a unique product_id
    3. Sets product type, pricing, and metadata
    4. Returns the complete product information
    
    **Path Parameters:**
    - `vendor_id`: The unique vendor identifier (e.g., "v_123")
    
    **Example Request:**
    ```json
    {
        "name": "Premium API Access",
        "description": "Monthly access to premium API features",
        "product_type": "subscription",
        "default_amount_usdc_minor": 9990000,
        "metadata": {
            "features": ["unlimited_requests", "priority_support"],
            "category": "api_access"
        }
    }
    ```
    """
    try:
        # Check if creating product for own vendor
        if current_vendor.vendor_id != vendor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only create products for your own vendor"
            )
            
        # Override the vendor_id in product_data with the path parameter
        product_data.vendor_id = vendor_id
        return await service.create_product(product_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create product: {str(e)}"
        )


@router.get(
    "/{vendor_id}/products/",
    response_model=List[ProductResponse],
    summary="List Vendor Products",
    description="Retrieve all products for a vendor"
)
async def list_vendor_products(
    vendor_id: str = Path(..., description="Vendor ID"),
    current_vendor = Depends(get_current_vendor),
    service: ProductService = Depends(get_product_service)
) -> List[ProductResponse]:
    """
    Retrieve all products for a specific vendor.
    
    Returns a list of all products owned by the vendor, ordered by creation date (newest first).
    
    **Path Parameters:**
    - `vendor_id`: The unique vendor identifier (e.g., "v_123")
    
    **Returns:**
    - Array of product objects with complete information
    - Empty array if vendor has no products
    """
    try:
        # Check if listing products for own vendor
        if current_vendor.vendor_id != vendor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only list products for your own vendor"
            )
            
        return await service.list_vendor_products(vendor_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list products: {str(e)}"
        )


@router.get(
    "/{vendor_id}/products/{product_id}",
    response_model=ProductResponse,
    summary="Get Product Details",
    description="Retrieve specific product details"
)
async def get_product(
    vendor_id: str = Path(..., description="Vendor ID"),
    product_id: str = Path(..., description="Product ID"),
    service: ProductService = Depends(get_product_service)
) -> ProductResponse:
    """
    Retrieve specific product details.
    
    Returns complete product information including:
    - Product details and pricing
    - Product type and metadata
    - Creation and update timestamps
    
    **Path Parameters:**
    - `vendor_id`: The unique vendor identifier (e.g., "v_123")
    - `product_id`: The unique product identifier (e.g., "p_abc")
    """
    try:
        product = await service.get_product(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found"
            )
        
        # Verify product belongs to the vendor
        if product.vendor_id != vendor_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found for vendor {vendor_id}"
            )
        
        return product
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve product: {str(e)}"
        )


@router.patch(
    "/{vendor_id}/products/{product_id}",
    response_model=ProductResponse,
    summary="Update Product",
    description="Update product details and configuration"
)
async def update_product(
    vendor_id: str = Path(..., description="Vendor ID"),
    product_id: str = Path(..., description="Product ID"),
    update_data: ProductUpdate = ...,
    service: ProductService = Depends(get_product_service)
) -> ProductResponse:
    """
    Update product details and configuration.
    
    This endpoint allows partial updates - only include fields you want to change.
    All fields are optional in the update request.
    
    **Example Request:**
    ```json
    {
        "name": "Premium API Access v2",
        "description": "Enhanced monthly access with new features",
        "default_amount_usdc_minor": 12990000,
        "metadata": {
            "features": ["unlimited_requests", "priority_support", "webhooks"],
            "category": "api_access",
            "version": "2.0"
        }
    }
    ```
    
    **Path Parameters:**
    - `vendor_id`: The unique vendor identifier (e.g., "v_123")
    - `product_id`: The unique product identifier (e.g., "p_abc")
    """
    try:
        # First verify the product exists and belongs to vendor
        existing_product = await service.get_product(product_id)
        if not existing_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found"
            )
        
        if existing_product.vendor_id != vendor_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found for vendor {vendor_id}"
            )
        
        # Convert Pydantic model to dict, excluding None values
        update_dict = update_data.model_dump(exclude_none=True)
        
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields provided for update"
            )
        
        updated_product = await service.update_product(product_id, update_dict)
        if not updated_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found"
            )
        
        return updated_product
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
            detail=f"Failed to update product: {str(e)}"
        )


@router.delete(
    "/{vendor_id}/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Product",
    description="Delete a product (only if no payment intents exist)"
)
async def delete_product(
    vendor_id: str = Path(..., description="Vendor ID"),
    product_id: str = Path(..., description="Product ID"),
    service: ProductService = Depends(get_product_service)
) -> None:
    """
    Delete a product.
    
    **Important:** Products can only be deleted if they have no associated payment intents.
    This is a safety measure to prevent data consistency issues.
    
    **Path Parameters:**
    - `vendor_id`: The unique vendor identifier (e.g., "v_123")
    - `product_id`: The unique product identifier (e.g., "p_abc")
    
    **Responses:**
    - `204 No Content`: Product successfully deleted
    - `400 Bad Request`: Product has associated payment intents and cannot be deleted
    - `404 Not Found`: Product not found or doesn't belong to vendor
    """
    try:
        # First verify the product exists and belongs to vendor
        existing_product = await service.get_product(product_id)
        if not existing_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found"
            )
        
        if existing_product.vendor_id != vendor_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found for vendor {vendor_id}"
            )
        
        # Attempt to delete
        deleted = await service.delete_product(product_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found"
            )
            
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
            detail=f"Failed to delete product: {str(e)}"
        )
