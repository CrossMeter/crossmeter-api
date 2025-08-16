from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any

from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionStatus
)
from app.services.subscription_service import SubscriptionService

router = APIRouter()


def get_subscription_service() -> SubscriptionService:
    """Dependency to get subscription service."""
    return SubscriptionService()


@router.post(
    "/",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Subscription",
    description="Create a new subscription for recurring payments"
)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    service: SubscriptionService = Depends(get_subscription_service)
) -> SubscriptionResponse:
    """
    Create a new subscription.
    
    This endpoint:
    1. Validates the vendor, product, and customer information
    2. Creates a subscription record with active status
    3. Calculates the next renewal date based on billing interval
    4. Returns the subscription details
    
    **Example Request:**
    ```json
    {
        "vendor_id": "v_123",
        "product_id": "p_abc",
        "plan_id": "plan_monthly_premium",
        "customer_email": "alice@example.com",
        "src_chain_id": 84532,
        "dest_chain_id": 8453,
        "billing_interval": "monthly",
        "amount_usdc_minor": 9990000
    }
    ```
    
    **Billing Intervals:**
    - `monthly`: 30 days
    - `quarterly`: 90 days  
    - `yearly`: 365 days
    """
    try:
        return await service.create_subscription(subscription_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription: {str(e)}"
        )


@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Get Subscription",
    description="Retrieve a subscription by ID with current status and renewal information"
)
async def get_subscription(
    subscription_id: str,
    service: SubscriptionService = Depends(get_subscription_service)
) -> SubscriptionResponse:
    """
    Get a subscription by its ID.
    
    Returns the current subscription details including:
    - Status (active, paused, cancelled, expired)
    - Next renewal date
    - Billing configuration
    - Customer information
    
    **Subscription Status Values:**
    - `active`: Subscription is active and will renew
    - `paused`: Subscription is temporarily paused
    - `cancelled`: Subscription has been cancelled
    - `expired`: Subscription has expired
    """
    subscription = await service.get_subscription(subscription_id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription not found: {subscription_id}"
        )
    
    return subscription


@router.post(
    "/{subscription_id}/renew",
    response_model=Dict[str, Any],
    summary="Renew Subscription",
    description="Create a new payment intent for subscription renewal"
)
async def renew_subscription(
    subscription_id: str,
    service: SubscriptionService = Depends(get_subscription_service)
) -> Dict[str, Any]:
    """
    Renew a subscription by creating a new payment intent.
    
    This endpoint:
    1. Validates the subscription is active
    2. Creates a new payment intent for the renewal amount
    3. Updates the next renewal date
    4. Returns the payment intent details for wallet execution
    
    **Usage Flow:**
    1. Call this endpoint when subscription is due for renewal
    2. Use the returned payment intent router information in your dApp
    3. Have customer sign and broadcast the transaction
    4. Call the payment intent `/tx/source` endpoint with the transaction hash
    
    **Example Response:**
    ```json
    {
        "subscription_id": "sub_xyz789",
        "payment_intent": {
            "intent_id": "pi_renewal_123",
            "status": "awaiting_user_tx",
            "amount_usdc_minor": 9990000,
            "router": {
                "address": "0xROUTER...",
                "chain_id": 84532,
                "function": "createPayment",
                "calldata": "0xabcdef..."
            }
        },
        "next_renewal_at": "2024-03-01T00:00:00Z"
    }
    ```
    """
    try:
        return await service.renew_subscription(subscription_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to renew subscription: {str(e)}"
        )


@router.patch(
    "/{subscription_id}/status",
    response_model=SubscriptionResponse,
    summary="Update Subscription Status",
    description="Update the status of a subscription (pause, cancel, reactivate)"
)
async def update_subscription_status(
    subscription_id: str,
    status_update: Dict[str, str],
    service: SubscriptionService = Depends(get_subscription_service)
) -> SubscriptionResponse:
    """
    Update subscription status.
    
    **Example Request:**
    ```json
    {
        "status": "paused"
    }
    ```
    
    **Valid Status Values:**
    - `active`: Reactivate subscription
    - `paused`: Pause subscription (stops auto-renewal)
    - `cancelled`: Cancel subscription permanently
    - `expired`: Mark subscription as expired
    
    **Note:** Once cancelled, a subscription cannot be reactivated.
    Create a new subscription instead.
    """
    if "status" not in status_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'status' field in request body"
        )
    
    try:
        new_status = SubscriptionStatus(status_update["status"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status_update['status']}. Valid values: {[s.value for s in SubscriptionStatus]}"
        )
    
    try:
        updated_subscription = await service.update_subscription_status(subscription_id, new_status)
        
        if not updated_subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription not found: {subscription_id}"
            )
        
        return updated_subscription
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update subscription status: {str(e)}"
        )
