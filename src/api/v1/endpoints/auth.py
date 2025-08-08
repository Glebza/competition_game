"""
Tournament Game Backend - Authentication API Endpoints
"""
from datetime import timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.schemas.user import (
    UserCreate,
    UserResponse,
    TokenResponse,
    GuestUserCreate,
    LoginRequest
)
from src.config import settings
from src.core.database import get_db
from src.core.security import (
    create_access_token,
    verify_password,
    get_password_hash
)
from src.modules.user import service as user_service
from src.modules.user.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
    InvalidCredentialsError
)

router = APIRouter()
security = HTTPBearer(auto_error=False)


@router.post("/guest", response_model=TokenResponse)
async def create_guest_session(
    guest_data: GuestUserCreate,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Create a guest user session
    
    Guest users can:
    - Create and manage competitions
    - Create and organize game sessions
    - Join other game sessions
    """
    try:
        # Create guest user
        guest_user = await user_service.create_guest_user(
            db=db,
            nickname=guest_data.nickname
        )
        
        # Generate access token
        access_token = create_access_token(
            subject=str(guest_user.id),
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            additional_claims={
                "type": "guest",
                "nickname": guest_user.nickname
            }
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=guest_user.id,
                nickname=guest_user.nickname,
                email=None,
                is_guest=True,
                created_at=guest_user.created_at
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create guest session: {str(e)}"
        )


@router.post("/register", response_model=TokenResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Register a new user account
    
    Registered users have all guest privileges plus:
    - Persistent account across sessions
    - Competition history
    - Profile customization
    """
    try:
        # Check if user exists
        existing_user = await user_service.get_user_by_email(db, user_data.email)
        if existing_user:
            raise UserAlreadyExistsError("User with this email already exists")
        
        # Create user
        user = await user_service.create_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            nickname=user_data.nickname
        )
        
        # Generate access token
        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            additional_claims={
                "type": "registered",
                "email": user.email
            }
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                nickname=user.nickname,
                email=user.email,
                is_guest=False,
                created_at=user.created_at
            )
        )
        
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Login with email and password
    """
    try:
        # Get user by email
        user = await user_service.get_user_by_email(db, login_data.email)
        if not user:
            raise InvalidCredentialsError("Invalid email or password")
        
        # Verify password
        if not user.password_hash or not verify_password(login_data.password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")
        
        # Generate access token
        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            additional_claims={
                "type": "registered",
                "email": user.email
            }
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                nickname=user.nickname,
                email=user.email,
                is_guest=False,
                created_at=user.created_at
            )
        )
        
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to login: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Get current user information
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Decode token and get user ID
        from src.api.deps import get_current_user_id
        user_id = await get_current_user_id(credentials)
        
        # Get user from database
        user = await user_service.get_user(db, user_id)
        if not user:
            raise UserNotFoundError("User not found")
        
        return UserResponse(
            id=user.id,
            nickname=user.nickname,
            email=user.email,
            is_guest=user.is_guest,
            created_at=user.created_at
        )
        
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh access token
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Decode current token and get user ID
        from src.api.deps import get_current_user_id
        user_id = await get_current_user_id(credentials)
        
        # Get user from database
        user = await user_service.get_user(db, user_id)
        if not user:
            raise UserNotFoundError("User not found")
        
        # Generate new access token
        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            additional_claims={
                "type": "guest" if user.is_guest else "registered",
                "email": user.email if not user.is_guest else None,
                "nickname": user.nickname
            }
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                nickname=user.nickname,
                email=user.email,
                is_guest=user.is_guest,
                created_at=user.created_at
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


@router.post("/convert-guest", response_model=TokenResponse)
async def convert_guest_to_registered(
    user_data: UserCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Convert a guest account to a registered account
    
    This preserves all competitions and game history
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Get current guest user
        from src.api.deps import get_current_user_id
        user_id = await get_current_user_id(credentials)
        
        user = await user_service.get_user(db, user_id)
        if not user or not user.is_guest:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only guest users can be converted"
            )
        
        # Check if email already exists
        existing_user = await user_service.get_user_by_email(db, user_data.email)
        if existing_user:
            raise UserAlreadyExistsError("User with this email already exists")
        
        # Convert guest to registered user
        updated_user = await user_service.convert_guest_to_registered(
            db=db,
            user_id=user_id,
            email=user_data.email,
            password=user_data.password
        )
        
        # Generate new access token
        access_token = create_access_token(
            subject=str(updated_user.id),
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            additional_claims={
                "type": "registered",
                "email": updated_user.email
            }
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=updated_user.id,
                nickname=updated_user.nickname,
                email=updated_user.email,
                is_guest=False,
                created_at=updated_user.created_at
            )
        )
        
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert account: {str(e)}"
        )
