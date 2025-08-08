# Common dependencies for API routes
"""
Tournament Game Backend - API Dependencies
Common dependencies used across API endpoints
"""
from typing import Optional, AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.database import async_session_maker
from src.modules.user import service as user_service


# Security scheme
security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    Ensures proper session cleanup after request.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def decode_token(token: str) -> dict:
    """
    Decode and validate JWT token
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """
    Get current user ID from JWT token.
    Raises 401 if token is invalid or missing.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = await decode_token(credentials.credentials)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        return UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UUID]:
    """
    Get current user ID from JWT token if provided.
    Returns None if no token is provided (for optional auth endpoints).
    """
    if not credentials:
        return None
    
    try:
        payload = await decode_token(credentials.credentials)
        user_id = payload.get("sub")
        
        if user_id:
            return UUID(user_id)
    except (HTTPException, ValueError):
        # Invalid token is treated as no token for optional auth
        return None
    
    return None


async def get_current_active_user(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Get current active user from database.
    Raises 401 if user not found or inactive.
    """
    user = await user_service.get_user(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_registered_user(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Get current user and ensure they are registered (not guest).
    Raises 403 if user is guest.
    """
    user = await user_service.get_user(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires a registered account"
        )
    
    return user


class RateLimitDep:
    """
    Rate limiting dependency.
    Can be used to limit requests per user or IP.
    """
    def __init__(self, calls: int = 10, period: int = 60):
        self.calls = calls
        self.period = period
        self.cache = {}  # In production, use Redis
    
    async def __call__(
        self,
        user_id: Optional[UUID] = Depends(get_current_user_id_optional)
    ):
        """
        Check rate limit for user.
        In MVP, this is a simple in-memory implementation.
        """
        # Simplified implementation for MVP
        # In production, implement with Redis
        key = str(user_id) if user_id else "anonymous"
        
        # For MVP, just pass through
        # TODO: Implement actual rate limiting
        return True


# Rate limit instances for different endpoints
rate_limit_strict = RateLimitDep(calls=10, period=60)  # 10 calls per minute
rate_limit_normal = RateLimitDep(calls=60, period=60)  # 60 calls per minute
rate_limit_relaxed = RateLimitDep(calls=120, period=60)  # 120 calls per minute


async def get_session_player(
    session_code: str,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id_optional)
):
    """
    Get player information for a session.
    Used to verify player is part of the session.
    """
    from src.modules.session import service as session_service
    
    session = await session_service.get_session_by_code(db, session_code.upper())
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if not user_id:
        return None
    
    player = await session_service.get_player_by_user_id(db, session.id, user_id)
    return player


async def verify_session_organizer(
    session_code: str,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Verify that the current user is the organizer of the session.
    Raises 403 if not organizer.
    """
    from src.modules.session import service as session_service
    
    session = await session_service.get_session_by_code(db, session_code.upper())
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session.organizer_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the session organizer can perform this action"
        )
    
    return session


async def verify_competition_owner(
    competition_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Verify that the current user owns the competition.
    Raises 403 if not owner.
    """
    from src.modules.competition import service as competition_service
    
    competition = await competition_service.get_competition(db, competition_id)
    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found"
        )
    
    if competition.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own competitions"
        )
    
    return competition
