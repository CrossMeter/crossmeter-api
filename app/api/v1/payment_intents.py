from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional

from app.schemas.payment_intent import (
    PaymentIntentCreate,
    PaymentIntentResponse,
    TransactionCompleteUpdate
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
    1. Validates the vendor and product exist and are related
    2. Gets price from product's default_amount_usdc_minor
    3. Gets destination chain and address from vendor's preferences
    4. Creates a payment intent record in 'created' status
    5. Returns the intent with price and destination info for user
    
    **Example Request:**
    ```json
    {
        "vendor_id": "v_123",
        "product_id": "p_abc"
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
    "/{intent_id}/complete",
    response_model=PaymentIntentResponse,
    summary="Complete Transaction",
    description="Complete the payment intent with transaction details"
)
async def complete_transaction(
    intent_id: str,
    transaction_update: TransactionCompleteUpdate,
    service: PaymentIntentService = Depends(get_payment_intent_service)
) -> PaymentIntentResponse:
    """
    Complete payment intent with transaction details.
    
    Call this endpoint when the transaction is completed to update the payment intent
    with all transaction details. Supports both successful and failed transactions:
    
    - **settled**: Payment succeeded, intent is complete
    - **failed**: Payment failed, user can retry with same intent_id
    
    **Example Success:**
    ```json
    {
        "transaction_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "payment_status": "settled",
        "source_chain_id": 84532,
        "source_address": "0x742d35Cc6635C0532925a3b8D19dac9dd9bf9876"
    }
    ```
    
    **Example Failure:**
    ```json
    {
        "transaction_hash": "0xfailed123456789abcdef123456789abcdef123456789abcdef123456789abcdef",
        "payment_status": "failed",
        "source_chain_id": 84532,
        "source_address": "0x742d35Cc6635C0532925a3b8D19dac9dd9bf9876"
    }
    ```
    """
    intent = await service.complete_transaction(intent_id, transaction_update)
    
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment intent not found: {intent_id}"
        )
    
    return intent
