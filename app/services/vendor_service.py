from datetime import datetime
from typing import Dict, Any, Optional
import secrets
from passlib.context import CryptContext
from app.database.client import get_supabase_admin_client
from app.schemas.vendor import VendorCreate, VendorResponse, VendorCreateWithWallet
from app.schemas.user import VendorStatusResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class VendorService:
    """Service for managing vendor operations."""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client()
    
    def generate_api_key(self) -> str:
        """Generate a secure API key."""
        return f"piaas_{secrets.token_urlsafe(32)}"
    
    async def create_vendor(self, vendor_data: VendorCreate) -> VendorResponse:
        """Create a new vendor."""
        try:
            # Generate vendor ID
            vendor_id = f"v_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Hash password and generate API key
            password_hash = pwd_context.hash(vendor_data.password)
            api_key = self.generate_api_key()
            
            # Prepare data for insertion
            insert_data = {
                "vendor_id": vendor_id,
                "name": vendor_data.name,
                "email": vendor_data.email,
                "password_hash": password_hash,
                "api_key": api_key,
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
            
            # Handle missing API key for existing vendors
            api_key = vendor_row.get("api_key")
            if not api_key:
                # Generate and save API key for existing vendor
                api_key = self.generate_api_key()
                try:
                    self.supabase.table("vendors").update({
                        "api_key": api_key
                    }).eq("vendor_id", vendor_row["vendor_id"]).execute()
                except:
                    # If update fails (e.g., column doesn't exist), continue with None
                    api_key = None
            
            return VendorResponse(
                vendor_id=vendor_row["vendor_id"],
                name=vendor_row["name"],
                email=vendor_row["email"],
                api_key=api_key,
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
    
    async def create_vendor_with_wallet(self, vendor_data: VendorCreateWithWallet, user_id: str) -> VendorResponse:
        """Create a new vendor with wallet authentication (no password) linked to a user."""
        try:
            # Check if vendor with this wallet address already exists
            existing_vendor = await self.get_vendor_by_wallet(vendor_data.wallet_address)
            if existing_vendor:
                raise ValueError(f"Vendor with wallet address {vendor_data.wallet_address} already exists")
            
            # Generate vendor ID
            vendor_id = f"v_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Generate API key (no password hash needed)
            api_key = self.generate_api_key()
            
            # Prepare data for insertion
            insert_data = {
                "vendor_id": vendor_id,
                "user_id": user_id,
                "name": vendor_data.name,
                "email": vendor_data.email,
                "api_key": api_key,
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
            
            # Handle missing API key for existing vendors
            api_key = vendor_row.get("api_key")
            if not api_key:
                # Generate and save API key for existing vendor
                api_key = self.generate_api_key()
                try:
                    self.supabase.table("vendors").update({
                        "api_key": api_key
                    }).eq("vendor_id", vendor_row["vendor_id"]).execute()
                except:
                    # If update fails (e.g., column doesn't exist), continue with None
                    api_key = None
            
            return VendorResponse(
                vendor_id=vendor_row["vendor_id"],
                name=vendor_row["name"],
                email=vendor_row["email"],
                api_key=api_key,
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
            
            # Handle missing API key for existing vendors
            api_key = vendor_row.get("api_key")
            if not api_key:
                # Generate and save API key for existing vendor
                api_key = self.generate_api_key()
                try:
                    self.supabase.table("vendors").update({
                        "api_key": api_key
                    }).eq("vendor_id", vendor_row["vendor_id"]).execute()
                except:
                    # If update fails (e.g., column doesn't exist), continue with None
                    api_key = None
            
            return VendorResponse(
                vendor_id=vendor_row["vendor_id"],
                name=vendor_row["name"],
                email=vendor_row["email"],
                api_key=api_key,
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
            
            # Handle missing API key for existing vendors
            api_key = vendor_row.get("api_key")
            if not api_key:
                # Generate and save API key for existing vendor
                api_key = self.generate_api_key()
                try:
                    self.supabase.table("vendors").update({
                        "api_key": api_key
                    }).eq("vendor_id", vendor_row["vendor_id"]).execute()
                except:
                    # If update fails (e.g., column doesn't exist), continue with None
                    api_key = None
            
            return VendorResponse(
                vendor_id=vendor_row["vendor_id"],
                name=vendor_row["name"],
                email=vendor_row["email"],
                api_key=api_key,
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
    
    async def regenerate_api_key(self, vendor_id: str) -> str:
        """Regenerate API key for a vendor."""
        try:
            new_api_key = self.generate_api_key()
            
            result = self.supabase.table("vendors").update({
                "api_key": new_api_key
            }).eq("vendor_id", vendor_id).execute()
            
            if not result.data:
                raise ValueError(f"Vendor {vendor_id} not found")
            
            return new_api_key
            
        except Exception as e:
            raise ValueError(f"Error regenerating API key: {str(e)}")
    
    async def get_vendor_by_api_key(self, api_key: str) -> Optional[VendorResponse]:
        """Get vendor by API key."""
        try:
            result = self.supabase.table("vendors").select("*").eq("api_key", api_key).execute()
            
            if not result.data:
                return None
            
            vendor_row = result.data[0]
            
            # Parse timestamps
            created_at = self._parse_timestamp(vendor_row["created_at"])
            updated_at = self._parse_timestamp(vendor_row["updated_at"])
            
            # Handle missing API key for existing vendors
            api_key = vendor_row.get("api_key")
            if not api_key:
                # Generate and save API key for existing vendor
                api_key = self.generate_api_key()
                try:
                    self.supabase.table("vendors").update({
                        "api_key": api_key
                    }).eq("vendor_id", vendor_row["vendor_id"]).execute()
                except:
                    # If update fails (e.g., column doesn't exist), continue with None
                    api_key = None
            
            return VendorResponse(
                vendor_id=vendor_row["vendor_id"],
                name=vendor_row["name"],
                email=vendor_row["email"],
                api_key=api_key,
                webhook_url=vendor_row["webhook_url"],
                preferred_dest_chain_id=vendor_row["preferred_dest_chain_id"],
                enabled_source_chains=vendor_row["enabled_source_chains"],
                wallet_address=vendor_row["wallet_address"],
                metadata=vendor_row["metadata"],
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            raise ValueError(f"Error fetching vendor by API key: {str(e)}")
    
    async def get_vendor_by_wallet(self, wallet_address: str) -> Optional[VendorResponse]:
        """Get vendor by wallet address (legacy method - use get_vendor_status_by_wallet instead)."""
        try:
            # First check if user exists
            user_result = self.supabase.table("users").select("id").eq("wallet_address", wallet_address).execute()
            
            if not user_result.data:
                return None
            
            user_id = user_result.data[0]["id"]
            
            # Check if vendor exists for this user
            vendor_result = self.supabase.table("vendors").select("*").eq("user_id", user_id).execute()
            
            if not vendor_result.data:
                return None
            
            vendor_row = vendor_result.data[0]
            
            # Parse timestamps
            created_at = self._parse_timestamp(vendor_row["created_at"])
            updated_at = self._parse_timestamp(vendor_row["updated_at"])
            
            # Handle missing API key for existing vendors
            api_key = vendor_row.get("api_key")
            if not api_key:
                # Generate and save API key for existing vendor
                api_key = self.generate_api_key()
                try:
                    self.supabase.table("vendors").update({
                        "api_key": api_key
                    }).eq("vendor_id", vendor_row["vendor_id"]).execute()
                except:
                    # If update fails (e.g., column doesn't exist), continue with None
                    api_key = None
            
            return VendorResponse(
                vendor_id=vendor_row["vendor_id"],
                name=vendor_row["name"],
                email=vendor_row["email"],
                api_key=api_key,
                webhook_url=vendor_row["webhook_url"],
                preferred_dest_chain_id=vendor_row["preferred_dest_chain_id"],
                enabled_source_chains=vendor_row["enabled_source_chains"],
                wallet_address=vendor_row["wallet_address"],
                metadata=vendor_row["metadata"],
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            raise ValueError(f"Error fetching vendor by wallet: {str(e)}")
    
    async def get_vendor_status_by_wallet(self, wallet_address: str) -> VendorStatusResponse:
        """Get vendor status by wallet address."""
        try:
            # First check if user exists
            user_result = self.supabase.table("users").select("id").eq("wallet_address", wallet_address).execute()
            
            if not user_result.data:
                # User doesn't exist, so vendor doesn't exist
                return VendorStatusResponse(
                    exists=False,
                    vendor=None,
                    isComplete=False
                )
            
            user_id = user_result.data[0]["id"]
            
            # Check if vendor exists for this user
            vendor_result = self.supabase.table("vendors").select("*").eq("user_id", user_id).execute()
            
            if not vendor_result.data:
                # User exists but no vendor profile
                return VendorStatusResponse(
                    exists=False,
                    vendor=None,
                    isComplete=False
                )
            
            vendor_row = vendor_result.data[0]
            
            # Parse timestamps
            created_at = self._parse_timestamp(vendor_row["created_at"])
            updated_at = self._parse_timestamp(vendor_row["updated_at"])
            
            # Handle missing API key for existing vendors
            api_key = vendor_row.get("api_key")
            if not api_key:
                # Generate and save API key for existing vendor
                api_key = self.generate_api_key()
                try:
                    self.supabase.table("vendors").update({
                        "api_key": api_key
                    }).eq("vendor_id", vendor_row["vendor_id"]).execute()
                except:
                    # If update fails (e.g., column doesn't exist), continue with None
                    api_key = None
            
            vendor_data = {
                "vendor_id": vendor_row["vendor_id"],
                "name": vendor_row["name"],
                "email": vendor_row["email"],
                "api_key": api_key,
                "webhook_url": vendor_row["webhook_url"],
                "preferred_dest_chain_id": vendor_row["preferred_dest_chain_id"],
                "enabled_source_chains": vendor_row["enabled_source_chains"],
                "wallet_address": vendor_row["wallet_address"],
                "metadata": vendor_row["metadata"],
                "created_at": created_at.isoformat(),
                "updated_at": updated_at.isoformat()
            }
            
            # Check if vendor profile is complete (has required fields)
            is_complete = bool(
                vendor_row["name"] and 
                vendor_row["email"] and 
                vendor_row["wallet_address"] and
                vendor_row["preferred_dest_chain_id"] and
                vendor_row["enabled_source_chains"]
            )
            
            return VendorStatusResponse(
                exists=True,
                vendor=vendor_data,
                isComplete=is_complete
            )
            
        except Exception as e:
            raise ValueError(f"Error checking vendor status: {str(e)}")
    
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
