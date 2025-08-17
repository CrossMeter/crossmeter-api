from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class LoginRequest(BaseModel):
    """Schema for login request."""
    email: EmailStr = Field(..., description="Vendor email")
    password: str = Field(..., description="Vendor password")


class WalletLoginRequest(BaseModel):
    """Schema for wallet-based login request."""
    walletAddress: str = Field(..., description="Ethereum wallet address")
    signature: Optional[str] = Field(None, description="Optional signature for verification")


class AuthResponse(BaseModel):
    """Schema for auth response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    vendor_id: str = Field(..., description="Vendor ID")


class WalletAuthResponse(BaseModel):
    """Schema for wallet-based auth response."""
    access_token: str = Field(..., description="JWT access token")
    vendor_id: str = Field(..., description="Vendor ID")


class TokenData(BaseModel):
    """Schema for JWT token data."""
    vendor_id: str = Field(..., description="Vendor ID")
