from datetime import datetime
from typing import Dict, Any, Optional
from passlib.context import CryptContext
from app.database.client import get_supabase_admin_client
from app.schemas.vendor import VendorCreate, VendorResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class VendorService:
    """Service for managing vendor operations."""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client()
    
    async def create_vendor(self, vendor_data: VendorCreate) -> VendorResponse:
        """Create a new vendor."""
        try:
            # Generate vendor ID
            vendor_id = f"v_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Hash password
            password_hash = pwd_context.hash(vendor_data.password)
            
            # Prepare data for insertion
            insert_data = {
                "vendor_id": vendor_id,
                "name": vendor_data.name,
                "email": vendor_data.email,
                "password_hash": password_hash,
                "webhook_url": vendor_data.webhook_url,
                "preferred_dest_chain_id": vendor_data.preferred_dest_chain_id,
                "enabled_source_chains": vendor_data.enabled_source_chains,
                "wallet_address": vendor_data.wallet_address,
                "metadata": vendor_data.metadata or {},
            }
            
            # Insert into database
            result = self.supabase.table("vendors").insert(insert_data).execute()
            
            if not result.data:
                raise ValueError("Failed to create vendor")
            
            vendor_row = result.data[0]
            
            # Parse timestamps
            created_at = self._parse_timestamp(vendor_row["created_at"])
            updated_at = self._parse_timestamp(vendor_row["updated_at"])
            
            return VendorResponse(
                vendor_id=vendor_row["vendor_id"],
                name=vendor_row["name"],
                email=vendor_row["email"],
                webhook_url=vendor_row["webhook_url"],
                preferred_dest_chain_id=vendor_row["preferred_dest_chain_id"],
                enabled_source_chains=vendor_row["enabled_source_chains"],
                wallet_address=vendor_row["wallet_address"],
                metadata=vendor_row["metadata"],
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            raise ValueError(f"Error creating vendor: {str(e)}")
    
    async def get_vendor(self, vendor_id: str) -> Optional[VendorResponse]:
        """Get vendor by ID."""
        try:
            result = self.supabase.table("vendors").select("*").eq("vendor_id", vendor_id).execute()
            
            if not result.data:
                return None
            
            vendor_row = result.data[0]
            
            # Parse timestamps
            created_at = self._parse_timestamp(vendor_row["created_at"])
            updated_at = self._parse_timestamp(vendor_row["updated_at"])
            
            return VendorResponse(
                vendor_id=vendor_row["vendor_id"],
                name=vendor_row["name"],
                email=vendor_row["email"],
                webhook_url=vendor_row["webhook_url"],
                preferred_dest_chain_id=vendor_row["preferred_dest_chain_id"],
                enabled_source_chains=vendor_row["enabled_source_chains"],
                wallet_address=vendor_row["wallet_address"],
                metadata=vendor_row["metadata"],
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            raise ValueError(f"Error fetching vendor: {str(e)}")
    
    async def update_vendor(self, vendor_id: str, update_data: Dict[str, Any]) -> Optional[VendorResponse]:
        """Update vendor by ID."""
        try:
            # Filter out None values and add updated_at
            filtered_data = {k: v for k, v in update_data.items() if v is not None}
            if not filtered_data:
                # If no updates, just return current vendor
                return await self.get_vendor(vendor_id)
            
            # Update in database
            result = self.supabase.table("vendors").update(filtered_data).eq("vendor_id", vendor_id).execute()
            
            if not result.data:
                return None
            
            vendor_row = result.data[0]
            
            # Parse timestamps
            created_at = self._parse_timestamp(vendor_row["created_at"])
            updated_at = self._parse_timestamp(vendor_row["updated_at"])
            
            return VendorResponse(
                vendor_id=vendor_row["vendor_id"],
                name=vendor_row["name"],
                email=vendor_row["email"],
                webhook_url=vendor_row["webhook_url"],
                preferred_dest_chain_id=vendor_row["preferred_dest_chain_id"],
                enabled_source_chains=vendor_row["enabled_source_chains"],
                wallet_address=vendor_row["wallet_address"],
                metadata=vendor_row["metadata"],
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            raise ValueError(f"Error updating vendor: {str(e)}")
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
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
