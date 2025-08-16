from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Dict, Any

from app.services.webhook_service import WebhookService

router = APIRouter()


def get_webhook_service() -> WebhookService:
    """Dependency to get webhook service."""
    return WebhookService()


@router.get(
    "/events/{vendor_id}",
    response_model=List[Dict[str, Any]],
    summary="Get Webhook Events",
    description="Retrieve webhook delivery events for a vendor"
)
async def get_webhook_events(
    vendor_id: str,
    limit: int = Query(default=50, le=100, description="Maximum number of events to return"),
    service: WebhookService = Depends(get_webhook_service)
) -> List[Dict[str, Any]]:
    """
    Get webhook delivery events for a vendor.
    
    Returns information about webhook delivery attempts including:
    - Event type and payload
    - Delivery status (pending, sent, failed, expired)
    - Attempt count and retry schedule
    - Response details from the webhook endpoint
    
    **Use this endpoint to debug webhook delivery issues.**
    """
    try:
        events = await service.get_webhook_events(vendor_id, limit)
        return events
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve webhook events: {str(e)}"
        )
    finally:
        await service.close()


@router.post(
    "/process",
    summary="Process Pending Webhooks",
    description="Manually trigger processing of pending webhook deliveries"
)
async def process_pending_webhooks(
    service: WebhookService = Depends(get_webhook_service)
) -> Dict[str, Any]:
    """
    Manually process all pending webhook deliveries.
    
    This endpoint:
    1. Finds all pending webhooks ready for retry
    2. Attempts delivery with exponential backoff
    3. Updates webhook status based on delivery result
    4. Schedules further retries if needed
    
    **Normally webhooks are processed automatically, but this endpoint 
    allows manual processing for debugging or immediate delivery.**
    """
    try:
        processed_count = await service.process_pending_webhooks()
        return {
            "message": f"Processed {processed_count} pending webhooks",
            "processed_count": processed_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhooks: {str(e)}"
        )
    finally:
        await service.close()


@router.delete(
    "/cleanup",
    summary="Cleanup Old Webhook Events",
    description="Remove old webhook events from the database"
)
async def cleanup_webhook_events(
    days_old: int = Query(default=30, ge=1, le=365, description="Delete events older than this many days"),
    service: WebhookService = Depends(get_webhook_service)
) -> Dict[str, Any]:
    """
    Clean up old webhook events from the database.
    
    This helps keep the webhook_events table from growing too large.
    Only deletes events older than the specified number of days.
    
    **Recommended to run this periodically (e.g., monthly) to maintain performance.**
    """
    try:
        deleted_count = await service.cleanup_old_webhook_events(days_old)
        return {
            "message": f"Deleted {deleted_count} old webhook events",
            "deleted_count": deleted_count,
            "cutoff_days": days_old
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup webhook events: {str(e)}"
        )
    finally:
        await service.close()
