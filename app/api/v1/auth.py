from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.schemas.auth import LoginRequest, AuthResponse, TokenData, WalletLoginRequest, WalletAuthResponse
from app.schemas.vendor import VendorCreate, VendorResponse
from app.services.auth_service import AuthService
from app.services.vendor_service import VendorService

router = APIRouter()
security = HTTPBearer()


def get_auth_service() -> AuthService:
    """Dependency to get auth service."""
    return AuthService()


def get_vendor_service() -> VendorService:
    """Dependency to get vendor service."""
    return VendorService()


async def get_current_vendor(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    vendor_service: VendorService = Depends(get_vendor_service)
) -> VendorResponse:
    """Get current authenticated vendor."""
    token_data = auth_service.verify_token(credentials.credentials)
    vendor = await vendor_service.get_vendor(token_data.vendor_id)
    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    return vendor


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Vendor",
    description="Create vendor account and return JWT token"
)
async def register(
    vendor_data: VendorCreate,
    auth_service: AuthService = Depends(get_auth_service),
    vendor_service: VendorService = Depends(get_vendor_service)
) -> AuthResponse:
    """Register new vendor and return JWT token."""
    try:
        # Create vendor
        vendor = await vendor_service.create_vendor(vendor_data)
        
        # Create JWT token
        access_token_expires = timedelta(minutes=30)
        access_token = auth_service.create_access_token(
            data={"sub": vendor.vendor_id}, expires_delta=access_token_expires
        )
        
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            vendor_id=vendor.vendor_id
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login Vendor",
    description="Authenticate vendor and return JWT token"
)
async def login(
    login_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    """Login vendor and return JWT token."""
    vendor_id = await auth_service.authenticate_vendor(login_data.email, login_data.password)
    
    if not vendor_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = auth_service.create_access_token(
        data={"sub": vendor_id}, expires_delta=access_token_expires
    )
    
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        vendor_id=vendor_id
    )


@router.post(
    "/login/wallet",
    response_model=WalletAuthResponse,
    summary="Wallet-based Login",
    description="Authenticate vendor by wallet address and return JWT token"
)
async def login_with_wallet(
    login_data: WalletLoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> WalletAuthResponse:
    """Login vendor with wallet address and return JWT token."""
    vendor_id = await auth_service.authenticate_vendor_by_wallet(login_data.walletAddress)
    
    if not vendor_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No vendor found with this wallet address",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = auth_service.create_access_token(
        data={"sub": vendor_id}, expires_delta=access_token_expires
    )
    
    return WalletAuthResponse(
        access_token=access_token,
        vendor_id=vendor_id
    )


@router.get(
    "/me",
    response_model=VendorResponse,
    summary="Get Current Vendor",
    description="Get current vendor info from JWT token"
)
async def get_me(
    current_vendor: VendorResponse = Depends(get_current_vendor)
) -> VendorResponse:
    """Get current authenticated vendor information."""
    return current_vendor
