from datetime import datetime
from typing import Optional
from app.database.client import get_supabase_admin_client
from app.schemas.user import UserCreate, UserResponse


class UserService:
    """Service for managing user operations."""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client()
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user with wallet address."""
        try:
            # Check if user with this wallet address already exists
            existing_user = await self.get_user_by_wallet(user_data.wallet_address)
            if existing_user:
                raise ValueError(f"User with wallet address {user_data.wallet_address} already exists")
            
            # Prepare data for insertion
            insert_data = {
                "wallet_address": user_data.wallet_address,
            }
            
            # Insert into database
            result = self.supabase.table("users").insert(insert_data).execute()
            
            if not result.data:
                raise ValueError("Failed to create user")
            
            user_row = result.data[0]
            
            # Parse timestamps
            created_at = self._parse_timestamp(user_row["created_at"])
            updated_at = self._parse_timestamp(user_row["updated_at"])
            
            return UserResponse(
                user_id=str(user_row["id"]),
                wallet_address=user_row["wallet_address"],
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            raise ValueError(f"Error creating user: {str(e)}")
    
    async def get_user_by_wallet(self, wallet_address: str) -> Optional[UserResponse]:
        """Get user by wallet address."""
        try:
            result = self.supabase.table("users").select("*").eq("wallet_address", wallet_address).execute()
            
            if not result.data:
                return None
            
            user_row = result.data[0]
            
            # Parse timestamps
            created_at = self._parse_timestamp(user_row["created_at"])
            updated_at = self._parse_timestamp(user_row["updated_at"])
            
            return UserResponse(
                user_id=str(user_row["id"]),
                wallet_address=user_row["wallet_address"],
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            raise ValueError(f"Error fetching user by wallet: {str(e)}")
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID."""
        try:
            result = self.supabase.table("users").select("*").eq("id", user_id).execute()
            
            if not result.data:
                return None
            
            user_row = result.data[0]
            
            # Parse timestamps
            created_at = self._parse_timestamp(user_row["created_at"])
            updated_at = self._parse_timestamp(user_row["updated_at"])
            
            return UserResponse(
                user_id=str(user_row["id"]),
                wallet_address=user_row["wallet_address"],
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            raise ValueError(f"Error fetching user by ID: {str(e)}")
    
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

