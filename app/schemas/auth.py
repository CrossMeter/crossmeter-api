from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Schema for login request."""
    email: EmailStr = Field(..., description="Vendor email")
    password: str = Field(..., description="Vendor password")


class AuthResponse(BaseModel):
    """Schema for auth response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    vendor_id: str = Field(..., description="Vendor ID")


class TokenData(BaseModel):
    """Schema for JWT token data."""
    vendor_id: str = Field(..., description="Vendor ID")
