from fastapi import APIRouter, HTTPException, Depends, status
from datetime import timedelta

from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService
from app.services.auth_service import AuthService

router = APIRouter()


def get_user_service() -> UserService:
    """Dependency to get user service."""
    return UserService()


def get_auth_service() -> AuthService:
    """Dependency to get auth service."""
    return AuthService()


@router.post(
    "/create-on-wallet-connect",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create User on Wallet Connect",
    description="Create a new user when wallet connects"
)
async def create_user_on_wallet_connect(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
) -> UserResponse:
    """
    Create a new user when a wallet connects.
    
    This endpoint:
    1. Validates the wallet address format
    2. Checks if user already exists with this wallet address
    3. Creates a new user record
    4. Returns the user information
    
    **Example Request:**
    ```json
    {
        "wallet_address": "0x1234567890123456789012345678901234567890"
    }
    ```
    
    **Returns:** User information with user_id and timestamps
    """
    try:
        return await user_service.create_user(user_data)
        
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

