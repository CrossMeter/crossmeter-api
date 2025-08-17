from fastapi import APIRouter, HTTPException, Depends, status, Header
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.schemas.vendor import VendorResponse
from app.schemas.product import ProductResponse
from app.schemas.payment_intent import PaymentIntentCreate, PaymentIntentResponse
from app.services.vendor_service import VendorService
from app.services.product_service import ProductService
from app.services.payment_intent_service import PaymentIntentService

router = APIRouter()


async def get_vendor_by_api_key(
    x_api_key: str = Header(..., description="API key for authentication"),
    vendor_service: VendorService = Depends(lambda: VendorService())
) -> VendorResponse:
    """Get vendor by API key from header."""
    if not x_api_key.startswith("piaas_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format"
        )
    
    vendor = await vendor_service.get_vendor_by_api_key(x_api_key)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return vendor


class ClientPaymentRequest(BaseModel):
    """Schema for client payment request."""
    product_id: str = Field(..., description="Product ID to charge for")
    metadata: Optional[dict] = Field(None, description="Additional payment metadata")


class VendorInfoResponse(BaseModel):
    """Schema for vendor information response."""
    vendor_id: str = Field(..., description="Vendor ID")
    name: str = Field(..., description="Vendor name")
    wallet_address: str = Field(..., description="Destination wallet address")
    preferred_dest_chain_id: int = Field(..., description="Preferred destination chain")
    enabled_source_chains: List[int] = Field(..., description="Chains customers can pay from")


class ProductInfoResponse(BaseModel):
    """Schema for product information response."""
    product_id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    product_type: str = Field(..., description="Product type")
    default_amount_usdc_minor: Optional[int] = Field(None, description="Default amount")


@router.get(
    "/vendor",
    response_model=VendorInfoResponse,
    summary="Get Vendor Info",
    description="Get vendor information using API key"
)
async def get_vendor_info(
    vendor: VendorResponse = Depends(get_vendor_by_api_key)
) -> VendorInfoResponse:
    """
    Get vendor information for client integration.
    
    **Headers:**
    - `X-API-Key`: Vendor API key (piaas_...)
    
    **Returns:**
    - Vendor details needed for payment processing
    - Destination wallet address
    - Supported chains for payment
    """
    return VendorInfoResponse(
        vendor_id=vendor.vendor_id,
        name=vendor.name,
        wallet_address=vendor.wallet_address,
        preferred_dest_chain_id=vendor.preferred_dest_chain_id,
        enabled_source_chains=vendor.enabled_source_chains
    )


@router.get(
    "/products",
    response_model=List[ProductInfoResponse],
    summary="List Products",
    description="Get all products for vendor using API key"
)
async def list_products(
    vendor: VendorResponse = Depends(get_vendor_by_api_key),
    product_service: ProductService = Depends(lambda: ProductService())
) -> List[ProductInfoResponse]:
    """
    List all products for the vendor.
    
    **Headers:**
    - `X-API-Key`: Vendor API key (piaas_...)
    
    **Returns:**
    - Array of products with pricing information
    - Product types and descriptions
    """
    products = await product_service.list_vendor_products(vendor.vendor_id)
    
    return [
        ProductInfoResponse(
            product_id=product.product_id,
            name=product.name,
            description=product.description,
            product_type=product.product_type.value,
            default_amount_usdc_minor=product.default_amount_usdc_minor
        )
        for product in products
    ]


@router.get(
    "/products/{product_id}",
    response_model=ProductInfoResponse,
    summary="Get Product Details",
    description="Get specific product details using API key"
)
async def get_product_details(
    product_id: str,
    vendor: VendorResponse = Depends(get_vendor_by_api_key),
    product_service: ProductService = Depends(lambda: ProductService())
) -> ProductInfoResponse:
    """
    Get specific product details.
    
    **Headers:**
    - `X-API-Key`: Vendor API key (piaas_...)
    
    **Path Parameters:**
    - `product_id`: Product identifier
    """
    product = await product_service.get_product(product_id)
    
    if not product or product.vendor_id != vendor.vendor_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return ProductInfoResponse(
        product_id=product.product_id,
        name=product.name,
        description=product.description,
        product_type=product.product_type.value,
        default_amount_usdc_minor=product.default_amount_usdc_minor
    )


@router.post(
    "/payment",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Payment Intent",
    description="Create payment intent for client payment gateway"
)
async def create_payment_intent(
    payment_request: ClientPaymentRequest,
    vendor: VendorResponse = Depends(get_vendor_by_api_key),
    product_service: ProductService = Depends(lambda: ProductService()),
    payment_service: PaymentIntentService = Depends(lambda: PaymentIntentService())
) -> PaymentIntentResponse:
    """
    Create a payment intent for the payment gateway.
    
    **Headers:**
    - `X-API-Key`: Vendor API key (piaas_...)
    
    **Body:**
    ```json
    {
        "product_id": "p_abc123",
        "metadata": {"order_id": "ord_123"}
    }
    ```
    
    **Returns:**
    - Payment intent with router calldata
    - Status: "awaiting_user_tx"
    - Router information for wallet execution
    """
    try:
        # Verify product belongs to vendor
        product = await product_service.get_product(payment_request.product_id)
        if not product or product.vendor_id != vendor.vendor_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Create payment intent data (simplified - only vendor_id and product_id needed)
        payment_data = PaymentIntentCreate(
            vendor_id=vendor.vendor_id,
            product_id=payment_request.product_id
        )
        
        # Create payment intent
        payment_intent = await payment_service.create_payment_intent(payment_data)
        
        return payment_intent
        
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
            detail=f"Failed to create payment intent: {str(e)}"
        )


@router.get(
    "/payment/{intent_id}",
    response_model=PaymentIntentResponse,
    summary="Get Payment Status",
    description="Get payment intent status and details"
)
async def get_payment_status(
    intent_id: str,
    vendor: VendorResponse = Depends(get_vendor_by_api_key),
    payment_service: PaymentIntentService = Depends(lambda: PaymentIntentService())
) -> PaymentIntentResponse:
    """
    Get payment intent status and details.
    
    **Headers:**
    - `X-API-Key`: Vendor API key (piaas_...)
    
    **Path Parameters:**
    - `intent_id`: Payment intent identifier
    """
    try:
        payment_intent = await payment_service.get_payment_intent(intent_id)
        
        if not payment_intent or payment_intent.vendor_id != vendor.vendor_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment intent not found"
            )
        
        return payment_intent
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payment intent: {str(e)}"
        )


@router.post(
    "/payment/{intent_id}/submit",
    response_model=PaymentIntentResponse,
    summary="Submit Transaction Hash",
    description="Submit transaction hash after user payment"
)
async def submit_transaction_hash(
    intent_id: str,
    tx_data: dict,
    vendor: VendorResponse = Depends(get_vendor_by_api_key),
    payment_service: PaymentIntentService = Depends(lambda: PaymentIntentService())
) -> PaymentIntentResponse:
    """
    Submit transaction hash after customer pays.
    
    **Headers:**
    - `X-API-Key`: Vendor API key (piaas_...)
    
    **Path Parameters:**
    - `intent_id`: Payment intent identifier
    
    **Body:**
    ```json
    {
        "tx_hash": "0x1234567890abcdef..."
    }
    ```
    
    **Flow:**
    1. Customer signs transaction in wallet
    2. Frontend gets transaction hash
    3. Submit hash to this endpoint
    4. Status changes: awaiting_user_tx → submitted
    5. Webhook fired to vendor
    """
    try:
        # Verify payment intent belongs to vendor
        payment_intent = await payment_service.get_payment_intent(intent_id)
        
        if not payment_intent or payment_intent.vendor_id != vendor.vendor_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment intent not found"
            )
        
        # This endpoint is deprecated - use complete transaction instead
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This endpoint is deprecated. Use /complete endpoint instead."
        )
        
        return updated_payment
        
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
            detail=f"Failed to submit transaction hash: {str(e)}"
        )


@router.post(
    "/payment/{intent_id}/settle",
    response_model=PaymentIntentResponse,
    summary="Mark Payment Settled",
    description="Mark payment as settled with destination transaction hash"
)
async def settle_payment(
    intent_id: str,
    tx_data: dict,
    vendor: VendorResponse = Depends(get_vendor_by_api_key),
    payment_service: PaymentIntentService = Depends(lambda: PaymentIntentService())
) -> PaymentIntentResponse:
    """
    Mark payment as settled with destination transaction hash.
    
    **Headers:**
    - `X-API-Key`: Vendor API key (piaas_...)
    
    **Path Parameters:**
    - `intent_id`: Payment intent identifier
    
    **Body:**
    ```json
    {
        "tx_hash": "0xabcdef1234567890..."
    }
    ```
    
    **Flow:**
    1. Vendor receives funds on destination chain
    2. Submit destination transaction hash
    3. Status changes: submitted → settled
    4. Final webhook fired
    """
    try:
        # Verify payment intent belongs to vendor
        payment_intent = await payment_service.get_payment_intent(intent_id)
        
        if not payment_intent or payment_intent.vendor_id != vendor.vendor_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment intent not found"
            )
        
        # This endpoint is deprecated - use complete transaction instead
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This endpoint is deprecated. Use /complete endpoint instead."
        )
        
        return updated_payment
        
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
            detail=f"Failed to settle payment: {str(e)}"
        )
