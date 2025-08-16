from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional

from app.schemas.payment_intent import (
    PaymentIntentCreate,
    PaymentIntentResponse,
    TransactionHashUpdate
)
from app.services.payment_intent_service import PaymentIntentService

router = APIRouter()


def get_payment_intent_service() -> PaymentIntentService:
    """Dependency to get payment intent service."""
    return PaymentIntentService()


@router.post(
    "/",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Payment Intent",
    description="Create a new payment intent with router calldata for cross-chain payment"
)
async def create_payment_intent(
    payment_data: PaymentIntentCreate,
    service: PaymentIntentService = Depends(get_payment_intent_service)
) -> PaymentIntentResponse:
    """
    Create a new payment intent.
    
    This endpoint:
    1. Validates the vendor, product, and chain combination
    2. Generates router contract calldata for the payment
    3. Creates a payment intent record in awaiting_user_tx status
    4. Returns the intent with router information for wallet execution
    
    **Example Request:**
    ```json
    {
        "vendor_id": "v_123",
        "product_id": "p_abc",
        "src_chain_id": 84532,
        "dest_chain_id": 8453,
        "amount_usdc_minor": 990000,
        "customer_email": "alice@example.com"
    }
    ```
    """
    try:
        return await service.create_payment_intent(payment_data)
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
    "/{intent_id}",
    response_model=PaymentIntentResponse,
    summary="Get Payment Intent",
    description="Retrieve a payment intent by ID with current status and transaction hashes"
)
async def get_payment_intent(
    intent_id: str,
    service: PaymentIntentService = Depends(get_payment_intent_service)
) -> PaymentIntentResponse:
    """
    Get a payment intent by its ID.
    
    Returns the current status and any known transaction hashes.
    The router information is included for client convenience.
    
    **Possible Status Values:**
    - `created`: Intent exists, calldata ready
    - `awaiting_user_tx`: Returned to client, waiting for wallet broadcast
    - `submitted`: Client posted source transaction hash
    - `settled`: Destination transaction hash confirmed
    """
    intent = await service.get_payment_intent(intent_id)
    
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment intent not found: {intent_id}"
        )
    
    return intent


@router.post(
    "/{intent_id}/tx/source",
    response_model=PaymentIntentResponse,
    summary="Update Source Transaction Hash",
    description="Report the source chain transaction hash after wallet broadcast"
)
async def update_source_transaction(
    intent_id: str,
    tx_update: TransactionHashUpdate,
    service: PaymentIntentService = Depends(get_payment_intent_service)
) -> PaymentIntentResponse:
    """
    Update payment intent with source transaction hash.
    
    Call this endpoint after the user broadcasts the transaction on the source chain.
    This moves the payment intent status from `awaiting_user_tx` to `submitted`.
    
    **Example Request:**
    ```json
    {
        "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    }
    ```
    
    This will trigger a `payment_intent.submitted` webhook to the vendor.
    """
    intent = await service.update_source_transaction(intent_id, tx_update)
    
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment intent not found: {intent_id}"
        )
    
    # TODO: Trigger webhook for payment_intent.submitted
    
    return intent


@router.post(
    "/{intent_id}/tx/destination",
    response_model=PaymentIntentResponse,
    summary="Update Destination Transaction Hash",
    description="Report the destination chain transaction hash when payment is settled"
)
async def update_destination_transaction(
    intent_id: str,
    tx_update: TransactionHashUpdate,
    service: PaymentIntentService = Depends(get_payment_intent_service)
) -> PaymentIntentResponse:
    """
    Update payment intent with destination transaction hash.
    
    This is optional and typically called when the vendor confirms
    receipt of payment on the destination chain. This moves the status to `settled`.
    
    **Example Request:**
    ```json
    {
        "tx_hash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    }
    ```
    
    This will trigger a `payment_intent.settled` webhook to the vendor.
    """
    intent = await service.update_destination_transaction(intent_id, tx_update)
    
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment intent not found: {intent_id}"
        )
    
    # TODO: Trigger webhook for payment_intent.settled
    
    return intent
