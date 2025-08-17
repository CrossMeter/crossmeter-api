from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.database.client import get_supabase_admin_client
from app.schemas.auth import TokenData

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client()
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    async def authenticate_vendor(self, email: str, password: str) -> Optional[str]:
        """Authenticate vendor and return vendor_id if valid."""
        try:
            result = self.supabase.table("vendors").select("vendor_id, password_hash").eq("email", email).execute()
            
            if not result.data:
                return None
            
            vendor = result.data[0]
            
            if not self.verify_password(password, vendor["password_hash"]):
                return None
                
            return vendor["vendor_id"]
            
        except Exception:
            return None
    
    async def authenticate_vendor_by_wallet(self, wallet_address: str) -> Optional[str]:
        """Authenticate vendor by wallet address and return vendor_id if valid."""
        try:
            # First check if user exists
            user_result = self.supabase.table("users").select("id").eq("wallet_address", wallet_address).execute()
            
            if not user_result.data:
                return None
            
            user_id = user_result.data[0]["id"]
            
            # Then check if vendor exists for this user
            vendor_result = self.supabase.table("vendors").select("vendor_id").eq("user_id", user_id).execute()
            
            if not vendor_result.data:
                return None
            
            vendor = vendor_result.data[0]
            return vendor["vendor_id"]
            
        except Exception:
            return None
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> TokenData:
        """Verify JWT token and return token data."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            vendor_id: str = payload.get("sub")
            if vendor_id is None:
                raise credentials_exception
            token_data = TokenData(vendor_id=vendor_id)
        except JWTError:
            raise credentials_exception
        return token_data
