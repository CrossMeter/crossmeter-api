from fastapi import APIRouter, HTTPException, Depends, status, Query, Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.database.client import get_supabase_admin_client
from app.schemas.payment_intent import PaymentIntentResponse, PaymentIntentStatus
from .auth import get_current_vendor

router = APIRouter()


class AnalyticsSummary(BaseModel):
    """Schema for analytics summary response."""
    total_revenue_usdc_minor: int = Field(..., description="Total revenue in USDC minor units")
    total_payments: int = Field(..., description="Total number of payments")
    successful_payments: int = Field(..., description="Number of successful payments")
    pending_payments: int = Field(..., description="Number of pending payments")
    average_payment_amount: float = Field(..., description="Average payment amount in USDC minor units")
    revenue_by_product: Dict[str, Dict[str, Any]] = Field(..., description="Revenue breakdown by product")
    payments_by_status: Dict[str, int] = Field(..., description="Payment count by status")
    recent_activity: List[Dict[str, Any]] = Field(..., description="Recent payment activity")


def get_supabase_client():
    """Dependency to get Supabase client."""
    return get_supabase_admin_client()


def _parse_timestamp(timestamp_str: str) -> datetime:
    """Parse Supabase timestamp with high precision."""
    if timestamp_str.endswith('Z'):
        timestamp_str = timestamp_str[:-1] + '+00:00'
    
    # Handle microseconds precision
    if '.' in timestamp_str:
        dt_part, rest = timestamp_str.split('.')
        if '+' in rest:
            micro_part, tz_part = rest.split('+')
            micro_part = micro_part[:6].ljust(6, '0')  # Ensure 6 digits
            timestamp_str = f"{dt_part}.{micro_part}+{tz_part}"
    
    return datetime.fromisoformat(timestamp_str)


@router.get(
    "/{vendor_id}/payment_intents/",
    response_model=List[Dict[str, Any]],
    summary="List Vendor Payment History",
    description="Retrieve payment intent history for a vendor with filtering options"
)
async def list_vendor_payment_intents(
    vendor_id: str = Path(..., description="Vendor ID"),
    status_filter: Optional[PaymentIntentStatus] = Query(None, description="Filter by payment status"),
    limit: int = Query(default=50, le=100, description="Maximum number of payment intents to return"),
    offset: int = Query(default=0, ge=0, description="Number of payment intents to skip"),
    current_vendor = Depends(get_current_vendor),
    supabase=Depends(get_supabase_client)
) -> List[Dict[str, Any]]:
    """
    Retrieve payment intent history for a vendor.
    
    Returns a list of payment intents with detailed information including:
    - Payment amounts and status
    - Product and customer details
    - Transaction hashes (when available)
    - Chain information
    - Timestamps
    
    **Query Parameters:**
    - `status`: Filter by payment status (created, awaiting_user_tx, submitted, settled)
    - `limit`: Maximum number of results (default: 50, max: 100)
    - `offset`: Skip number of results for pagination (default: 0)
    
    **Path Parameters:**
    - `vendor_id`: The unique vendor identifier (e.g., "v_123")
    """
    try:
        # Check if accessing own vendor's payment history
        if current_vendor.vendor_id != vendor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only access your own payment history"
            )
            
        # Build query
        query = (supabase
                .table("payment_intents")
                .select("""
                    *,
                    products!inner(name, product_type)
                """)
                .eq("vendor_id", vendor_id)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1))
        
        # Apply status filter if provided
        if status_filter:
            query = query.eq("status", status_filter.value)
        
        result = query.execute()
        
        # Format response
        payment_intents = []
        for row in result.data:
            # Parse timestamps
            created_at = _parse_timestamp(row["created_at"])
            updated_at = _parse_timestamp(row["updated_at"])
            
            payment_intents.append({
                "intent_id": row["intent_id"],
                "status": row["status"],
                "amount_usdc_minor": row["price_usdc_minor"],
                "src_chain_id": row["source_chain_id"],
                "dest_chain_id": row["destination_chain_id"],
                "src_tx_hash": row["transaction_hash"],
                "dest_tx_hash": row["transaction_hash"],  # Using same hash for both since schema only has one
                "transaction_hash": row["transaction_hash"],
                "product": {
                    "product_id": row["product_id"],
                    "name": row["products"]["name"] if row["products"] else None,
                    "type": row["products"]["product_type"] if row["products"] else None
                },
                "created_at": created_at.isoformat(),
                "updated_at": updated_at.isoformat()
            })
        
        return payment_intents
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payment history: {str(e)}"
        )


@router.get(
    "/{vendor_id}/analytics",
    response_model=AnalyticsSummary,
    summary="Get Vendor Analytics",
    description="Retrieve comprehensive analytics and revenue summary for a vendor"
)
async def get_vendor_analytics(
    vendor_id: str = Path(..., description="Vendor ID"),
    days: int = Query(default=30, ge=1, le=365, description="Number of days to include in analytics"),
    current_vendor = Depends(get_current_vendor),
    supabase=Depends(get_supabase_client)
) -> AnalyticsSummary:
    """
    Retrieve comprehensive analytics and revenue summary for a vendor.
    
    Returns detailed analytics including:
    - Total revenue and payment counts
    - Success rates and status breakdown
    - Revenue breakdown by product
    - Recent payment activity
    - Performance metrics
    
    **Query Parameters:**
    - `days`: Number of days to include in analytics (default: 30, max: 365)
    
    **Path Parameters:**
    - `vendor_id`: The unique vendor identifier (e.g., "v_123")
    
    **Example Response:**
    ```json
    {
        "total_revenue_usdc_minor": 15750000,
        "total_payments": 42,
        "successful_payments": 38,
        "pending_payments": 4,
        "average_payment_amount": 375000.0,
        "revenue_by_product": {
            "p_abc": {
                "product_name": "Premium API",
                "revenue": 12000000,
                "count": 30
            }
        },
        "payments_by_status": {
            "settled": 35,
            "submitted": 3,
            "awaiting_user_tx": 4
        }
    }
    ```
    """
    try:
        # Check if accessing own vendor's analytics
        if current_vendor.vendor_id != vendor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only access your own analytics"
            )
            
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get payment intents with product details
        result = (supabase
                 .table("payment_intents")
                 .select("""
                     *,
                     products!inner(name, product_type)
                 """)
                 .eq("vendor_id", vendor_id)
                 .gte("created_at", start_date.isoformat())
                 .lte("created_at", end_date.isoformat())
                 .order("created_at", desc=True)
                 .execute())
        
        payments = result.data
        
        # Calculate basic metrics
        total_payments = len(payments)
        successful_payments = len([p for p in payments if p["status"] in ["submitted", "settled"]])
        pending_payments = len([p for p in payments if p["status"] in ["created", "awaiting_user_tx"]])
        
        # Calculate revenue (only for successful payments)
        successful_payment_amounts = [
            p["price_usdc_minor"] for p in payments 
            if p["status"] in ["submitted", "settled"] and p["price_usdc_minor"]
        ]
        total_revenue = sum(successful_payment_amounts)
        average_payment = sum(successful_payment_amounts) / len(successful_payment_amounts) if successful_payment_amounts else 0
        
        # Revenue by product
        revenue_by_product = {}
        for payment in payments:
            if payment["status"] in ["submitted", "settled"] and payment["price_usdc_minor"]:
                product_id = payment["product_id"]
                if product_id not in revenue_by_product:
                    revenue_by_product[product_id] = {
                        "product_name": payment["products"]["name"] if payment["products"] else "Unknown",
                        "product_type": payment["products"]["product_type"] if payment["products"] else "unknown",
                        "revenue": 0,
                        "count": 0
                    }
                revenue_by_product[product_id]["revenue"] += payment["price_usdc_minor"]
                revenue_by_product[product_id]["count"] += 1
        
        # Payments by status
        payments_by_status = {}
        for payment in payments:
            status_key = payment["status"]
            payments_by_status[status_key] = payments_by_status.get(status_key, 0) + 1
        
        # Recent activity (last 10 payments)
        recent_activity = []
        for payment in payments[:10]:
            created_at = _parse_timestamp(payment["created_at"])
            recent_activity.append({
                "intent_id": payment["id"],
                "price_usdc_minor": payment["price_usdc_minor"],
                "status": payment["status"],
                "product_name": payment["products"]["name"] if payment["products"] else "Unknown",
                "created_at": created_at.isoformat(),
                "destination_chain_id": payment["destination_chain_id"],
                "destination_address": payment["destination_address"]
            })
        
        return AnalyticsSummary(
            total_revenue_usdc_minor=total_revenue,
            total_payments=total_payments,
            successful_payments=successful_payments,
            pending_payments=pending_payments,
            average_payment_amount=average_payment,
            revenue_by_product=revenue_by_product,
            payments_by_status=payments_by_status,
            recent_activity=recent_activity
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analytics: {str(e)}"
        )
