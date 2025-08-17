from fastapi import APIRouter, HTTPException, Query, status
from typing import Dict, Any, List, Optional

from app.services.router_service import RouterService
from app.services.contract_interface import ChainConfig, PaymentType
from app.services.product_service import ProductService
from app.services.vendor_service import VendorService

router = APIRouter()


@router.get(
    "/chains",
    response_model=List[Dict[str, Any]],
    summary="Get Supported Chains",
    description="Retrieve list of all supported blockchain networks with their configurations"
)
async def get_supported_chains() -> List[Dict[str, Any]]:
    """
    Get all supported blockchain networks.
    
    Returns information about each supported chain including:
    - Chain ID and name
    - Router contract address
    - USDC token address
    - Gas limits and bridge fees
    - Network-specific configuration
    
    **Use this endpoint to show available networks in your UI.**
    """
    supported_chains = ChainConfig.get_supported_chains()
    chains_info = []
    
    for chain_id in supported_chains:
        config = ChainConfig.get_chain_config(chain_id)
        if config:
            chains_info.append({
                "chain_id": chain_id,
                **config
            })
    
    return chains_info


@router.get(
    "/chains/{chain_id}",
    response_model=Dict[str, Any],
    summary="Get Chain Information",
    description="Get detailed information about a specific blockchain network"
)
async def get_chain_info(chain_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific chain.
    
    Returns:
    - Network name and configuration
    - Router contract address
    - USDC token address
    - Gas limits and fee structure
    - Bridge configuration
    """
    chain_info = RouterService.get_chain_info(chain_id)
    
    if not chain_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chain {chain_id} is not supported"
        )
    
    return {
        "chain_id": chain_id,
        **chain_info
    }


@router.post(
    "/estimate",
    response_model=Dict[str, Any],
    summary="Estimate Payment Costs",
    description="Estimate gas costs and bridge fees for a payment"
)
async def estimate_payment_costs(
    request: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Estimate costs for a payment including gas and bridge fees.
    
    **Example Request:**
    ```json
    {
        "src_chain_id": 84532,
        "dest_chain_id": 8453,
        "amount_usdc_minor": 1000000
    }
    ```
    
    **Returns:**
    - Gas limit estimates for both chains
    - Bridge fees (if cross-chain)
    - Total cost breakdown
    - Chain-specific information
    """
    try:
        src_chain_id = request.get("src_chain_id")
        dest_chain_id = request.get("dest_chain_id")
        amount_usdc_minor = request.get("amount_usdc_minor")
        
        if not all([src_chain_id, dest_chain_id, amount_usdc_minor]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: src_chain_id, dest_chain_id, amount_usdc_minor"
            )
        
        estimation = RouterService.estimate_gas_cost(
            src_chain_id=src_chain_id,
            dest_chain_id=dest_chain_id,
            amount_usdc_minor=amount_usdc_minor
        )
        
        if "error" in estimation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=estimation["error"]
            )
        
        return estimation
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/generate-calldata",
    response_model=Dict[str, Any],
    summary="Generate Router Calldata",
    description="Generate contract calldata for a payment transaction"
)
async def generate_payment_calldata(
    request: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate router contract calldata for a payment.
    
    **Example Request:**
    ```json
    {
        "vendor_wallet": "0x1234567890123456789012345678901234567890",
        "amount_usdc_minor": 1000000,
        "src_chain_id": 84532,
        "dest_chain_id": 8453,
        "payment_intent_id": "pi_test123",
        "payment_type": "bridge"
    }
    ```
    
    **Returns:**
    - Router contract address
    - Function name to call
    - Encoded calldata
    - Gas limit estimate
    - Bridge fee calculation
    - Total cost estimate
    """
    try:
        vendor_wallet = request.get("vendor_wallet")
        amount_usdc_minor = request.get("amount_usdc_minor")
        src_chain_id = request.get("src_chain_id")
        dest_chain_id = request.get("dest_chain_id")
        payment_intent_id = request.get("payment_intent_id")
        payment_type = request.get("payment_type", "simple")
        bridge_address = request.get("bridge_address")
        
        if not all([vendor_wallet, amount_usdc_minor, src_chain_id, dest_chain_id, payment_intent_id]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: vendor_wallet, amount_usdc_minor, src_chain_id, dest_chain_id, payment_intent_id"
            )
        
        # Validate payment type
        try:
            payment_type_enum = PaymentType(payment_type)
        except ValueError:
            payment_type_enum = PaymentType.SIMPLE
        
        calldata_info = RouterService.generate_payment_calldata(
            vendor_wallet=vendor_wallet,
            amount_usdc_minor=amount_usdc_minor,
            src_chain_id=src_chain_id,
            dest_chain_id=dest_chain_id,
            payment_intent_id=payment_intent_id,
            payment_type=payment_type_enum,
            bridge_address=bridge_address
        )
        
        return calldata_info
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/validate",
    response_model=Dict[str, Any],
    summary="Validate Chain Combination",
    description="Check if a chain combination is supported for payments"
)
async def validate_chain_combination(
    src_chain_id: int = Query(..., description="Source chain ID"),
    dest_chain_id: int = Query(..., description="Destination chain ID")
) -> Dict[str, Any]:
    """
    Validate if a chain combination is supported.
    
    **Query Parameters:**
    - `src_chain_id`: Source chain ID (where customer pays from)
    - `dest_chain_id`: Destination chain ID (where vendor receives)
    
    **Returns:**
    - Validation result
    - Supported payment types
    - Chain information
    - Estimated costs
    """
    is_supported = RouterService.validate_chain_support(src_chain_id, dest_chain_id)
    
    if not is_supported:
        return {
            "supported": False,
            "reason": "One or both chains are not supported",
            "src_chain_id": src_chain_id,
            "dest_chain_id": dest_chain_id
        }
    
    # Get chain information
    src_config = ChainConfig.get_chain_config(src_chain_id)
    dest_config = ChainConfig.get_chain_config(dest_chain_id)
    
    # Determine supported payment types
    payment_types = ["simple"]
    if src_chain_id != dest_chain_id:
        payment_types.append("bridge")
    
    return {
        "supported": True,
        "src_chain_id": src_chain_id,
        "dest_chain_id": dest_chain_id,
        "src_chain": src_config,
        "dest_chain": dest_config,
        "payment_types": payment_types,
        "is_cross_chain": src_chain_id != dest_chain_id,
        "bridge_fee_bps": src_config.get("bridge_fee_bps", 0) if src_chain_id != dest_chain_id else 0
    }


@router.get(
    "/vendor/{vendor_id}/products",
    response_model=Dict[str, Any],
    summary="Get Vendor Products",
    description="Retrieve vendor information and all products for a specific vendor by vendor ID"
)
async def get_vendor_products(vendor_id: str) -> Dict[str, Any]:
    """
    Get vendor information and all products for a specific vendor.
    
    **Path Parameters:**
    - `vendor_id`: The vendor identifier (e.g., "v_20241201120000")
    
    **Returns:**
    Vendor information including wallet address, preferred chain, and list of products.
    
    **Use this endpoint to display vendor products without authentication.**
    """
    try:
        vendor_service = VendorService()
        product_service = ProductService()
        
        # Get vendor information
        vendor = await vendor_service.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vendor {vendor_id} not found"
            )
        
        # Get vendor products
        products = await product_service.list_vendor_products(vendor_id)
        
        # Convert ProductResponse objects to dictionaries
        product_list = []
        for product in products:
            product_list.append({
                "product_id": product.product_id,
                "name": product.name,
                "description": product.description,
                "product_type": product.product_type.value,
                "default_amount_usdc_minor": product.default_amount_usdc_minor,
                "created_at": product.created_at.isoformat() if product.created_at else None
            })
        
        # Get preferred chain name
        preferred_chain_name = None
        if vendor.preferred_dest_chain_id:
            chain_config = ChainConfig.get_chain_config(vendor.preferred_dest_chain_id)
            if chain_config:
                preferred_chain_name = chain_config.get("name")
        
        return {
            "vendor_id": vendor.vendor_id,
            "vendor_name": vendor.name,
            "wallet_address": vendor.wallet_address,
            "preferred_dest_chain_id": vendor.preferred_dest_chain_id,
            "preferred_chain_name": preferred_chain_name,
            "enabled_source_chains": vendor.enabled_source_chains,
            "products": product_list
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve vendor information: {str(e)}"
        )
