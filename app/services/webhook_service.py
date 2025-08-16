import uuid
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
import httpx
from supabase import Client

from app.database.client import get_database_client
from app.schemas.webhook import WebhookPayload, WebhookEventType
from app.core.config import settings


class WebhookStatus(str, Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    EXPIRED = "expired"


class WebhookService:
    """Service for managing webhook delivery with retry logic."""
    
    def __init__(self, db_client: Optional[Client] = None):
        self.db = db_client or get_database_client()
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.webhook_timeout_seconds),
            follow_redirects=True
        )
    
    async def send_webhook(
        self,
        vendor_id: str,
        event_type: WebhookEventType,
        payload_data: Dict[str, Any]
    ) -> bool:
        """
        Send a webhook to a vendor with retry logic.
        
        Args:
            vendor_id: Vendor identifier
            event_type: Type of webhook event
            payload_data: Webhook payload data
            
        Returns:
            bool: True if webhook was queued successfully
        """
        # Get vendor webhook URL
        vendor_result = self.db.table("vendors").select("webhook_url").eq("vendor_id", vendor_id).execute()
        
        if not vendor_result.data or not vendor_result.data[0]["webhook_url"]:
            # Vendor has no webhook URL configured, skip silently
            return True
        
        webhook_url = vendor_result.data[0]["webhook_url"]
        
        # Create webhook payload
        webhook_payload = WebhookPayload(
            event_type=event_type,
            vendor_id=vendor_id,
            timestamp=datetime.utcnow(),
            **payload_data
        )
        
        # Store webhook event in database for tracking
        webhook_event_id = await self._create_webhook_event(
            vendor_id=vendor_id,
            event_type=event_type,
            payload=webhook_payload.model_dump(),
            webhook_url=webhook_url
        )
        
        # Attempt immediate delivery
        success = await self._attempt_webhook_delivery(webhook_event_id, webhook_url, webhook_payload)
        
        if not success:
            # Schedule retry
            await self._schedule_retry(webhook_event_id)
        
        return True
    
    async def process_pending_webhooks(self) -> int:
        """
        Process all pending webhook deliveries.
        
        Returns:
            int: Number of webhooks processed
        """
        # Get pending webhooks that are ready for retry
        now = datetime.utcnow()
        pending_webhooks = self.db.table("webhook_events").select("*").eq("status", WebhookStatus.PENDING.value).lte("next_retry_at", now.isoformat()).execute()
        
        processed_count = 0
        
        for webhook_data in pending_webhooks.data:
            webhook_id = webhook_data["id"]
            webhook_url = webhook_data["webhook_url"]
            payload_dict = webhook_data["payload"]
            
            # Recreate webhook payload
            webhook_payload = WebhookPayload(**payload_dict)
            
            # Attempt delivery
            success = await self._attempt_webhook_delivery(webhook_id, webhook_url, webhook_payload)
            
            if not success:
                await self._schedule_retry(webhook_id)
            
            processed_count += 1
        
        return processed_count
    
    async def get_webhook_events(
        self, 
        vendor_id: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get webhook events for a vendor.
        
        Args:
            vendor_id: Vendor identifier
            limit: Maximum number of events to return
            
        Returns:
            List of webhook event records
        """
        result = self.db.table("webhook_events").select("*").eq("vendor_id", vendor_id).order("created_at", desc=True).limit(limit).execute()
        
        return result.data
    
    async def _create_webhook_event(
        self,
        vendor_id: str,
        event_type: WebhookEventType,
        payload: Dict[str, Any],
        webhook_url: str
    ) -> str:
        """
        Create a webhook event record in the database.
        
        Returns:
            str: Webhook event ID
        """
        now = datetime.utcnow()
        
        # Ensure payload timestamps are serialized as strings
        serialized_payload = self._serialize_payload(payload)
        
        webhook_event_data = {
            "vendor_id": vendor_id,
            "event_type": event_type.value,
            "payload": serialized_payload,
            "webhook_url": webhook_url,
            "status": WebhookStatus.PENDING.value,
            "attempts": 0,
            "max_attempts": settings.webhook_retry_attempts,
            "next_retry_at": now.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        result = self.db.table("webhook_events").insert(webhook_event_data).execute()
        
        if not result.data:
            raise Exception("Failed to create webhook event")
        
        return result.data[0]["id"]
    
    async def _attempt_webhook_delivery(
        self,
        webhook_event_id: str,
        webhook_url: str,
        payload: WebhookPayload
    ) -> bool:
        """
        Attempt to deliver a webhook.
        
        Returns:
            bool: True if delivery was successful
        """
        now = datetime.utcnow()
        
        # Get current webhook event to check attempts
        webhook_result = self.db.table("webhook_events").select("attempts, max_attempts").eq("id", webhook_event_id).execute()
        
        if not webhook_result.data:
            return False
        
        webhook_data = webhook_result.data[0]
        current_attempts = webhook_data["attempts"]
        max_attempts = webhook_data["max_attempts"]
        
        # Check if we've exceeded max attempts
        if current_attempts >= max_attempts:
            await self._mark_webhook_expired(webhook_event_id)
            return False
        
        try:
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": f"PIaaS-Webhooks/{settings.version}",
                "X-PIaaS-Event": payload.event_type,
                "X-PIaaS-Vendor-ID": payload.vendor_id,
                "X-PIaaS-Timestamp": payload.timestamp.isoformat(),
                # TODO: Add signature header for security
                # "X-PIaaS-Signature": self._generate_signature(payload)
            }
            
            # Send webhook with properly serialized payload
            serialized_payload = self._serialize_payload(payload.model_dump())
            response = await self.http_client.post(
                webhook_url,
                json=serialized_payload,
                headers=headers
            )
            
            # Update webhook event with attempt result
            update_data = {
                "attempts": current_attempts + 1,
                "last_attempt_at": now.isoformat(),
                "response_status": response.status_code,
                "response_body": response.text[:1000],  # Truncate to 1000 chars
                "updated_at": now.isoformat()
            }
            
            # Check if delivery was successful (2xx status codes)
            if 200 <= response.status_code < 300:
                update_data["status"] = WebhookStatus.SENT.value
                success = True
            else:
                update_data["status"] = WebhookStatus.FAILED.value
                success = False
            
            # Update database
            self.db.table("webhook_events").update(update_data).eq("id", webhook_event_id).execute()
            
            return success
            
        except Exception as e:
            # Handle delivery failure
            update_data = {
                "attempts": current_attempts + 1,
                "last_attempt_at": now.isoformat(),
                "response_status": 0,
                "response_body": f"Delivery failed: {str(e)}"[:1000],
                "status": WebhookStatus.FAILED.value,
                "updated_at": now.isoformat()
            }
            
            self.db.table("webhook_events").update(update_data).eq("id", webhook_event_id).execute()
            
            return False
    
    async def _schedule_retry(self, webhook_event_id: str) -> None:
        """
        Schedule the next retry attempt with exponential backoff.
        """
        # Get current attempt count
        webhook_result = self.db.table("webhook_events").select("attempts").eq("id", webhook_event_id).execute()
        
        if not webhook_result.data:
            return
        
        attempts = webhook_result.data[0]["attempts"]
        
        # Calculate exponential backoff: base_delay * (2 ^ attempts)
        base_delay = settings.webhook_retry_delay_seconds
        delay_seconds = base_delay * (2 ** (attempts - 1))
        
        # Cap maximum delay at 1 hour
        delay_seconds = min(delay_seconds, 3600)
        
        next_retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
        
        # Update webhook event with next retry time
        update_data = {
            "next_retry_at": next_retry_at.isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        self.db.table("webhook_events").update(update_data).eq("id", webhook_event_id).execute()
    
    async def _mark_webhook_expired(self, webhook_event_id: str) -> None:
        """
        Mark a webhook as expired after max attempts.
        """
        update_data = {
            "status": WebhookStatus.EXPIRED.value,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        self.db.table("webhook_events").update(update_data).eq("id", webhook_event_id).execute()
    
    async def cleanup_old_webhook_events(self, days_old: int = 30) -> int:
        """
        Clean up old webhook events.
        
        Args:
            days_old: Delete events older than this many days
            
        Returns:
            int: Number of events deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Delete old webhook events
        result = self.db.table("webhook_events").delete().lt("created_at", cutoff_date.isoformat()).execute()
        
        return len(result.data) if result.data else 0
    
    def _serialize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize payload for JSON storage, converting datetime objects to strings.
        """
        serialized = {}
        for key, value in payload.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = self._serialize_payload(value)
            else:
                serialized[key] = value
        return serialized
    
    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()


# Helper functions for easy webhook sending
async def send_payment_intent_webhook(
    vendor_id: str,
    event_type: WebhookEventType,
    intent_id: str,
    product_id: str,
    amount_usdc_minor: int,
    src_chain_id: int,
    dest_chain_id: int,
    src_tx_hash: Optional[str] = None,
    dest_tx_hash: Optional[str] = None,
    customer_email: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Send a payment intent webhook.
    """
    webhook_service = WebhookService()
    
    try:
        payload_data = {
            "intent_id": intent_id,
            "product_id": product_id,
            "amount_usdc_minor": amount_usdc_minor,
            "src_chain_id": src_chain_id,
            "dest_chain_id": dest_chain_id,
            "src_tx_hash": src_tx_hash,
            "dest_tx_hash": dest_tx_hash,
            "customer_email": customer_email,
            "metadata": metadata or {}
        }
        
        return await webhook_service.send_webhook(vendor_id, event_type, payload_data)
    
    finally:
        await webhook_service.close()


async def send_subscription_webhook(
    vendor_id: str,
    event_type: WebhookEventType,
    subscription_id: str,
    product_id: str,
    amount_usdc_minor: int,
    intent_id: Optional[str] = None,
    src_chain_id: Optional[int] = None,
    dest_chain_id: Optional[int] = None,
    customer_email: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Send a subscription webhook.
    """
    webhook_service = WebhookService()
    
    try:
        payload_data = {
            "subscription_id": subscription_id,
            "intent_id": intent_id,
            "product_id": product_id,
            "amount_usdc_minor": amount_usdc_minor,
            "src_chain_id": src_chain_id,
            "dest_chain_id": dest_chain_id,
            "customer_email": customer_email,
            "metadata": metadata or {}
        }
        
        return await webhook_service.send_webhook(vendor_id, event_type, payload_data)
    
    finally:
        await webhook_service.close()
