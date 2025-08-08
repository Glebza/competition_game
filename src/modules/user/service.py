"""
Tournament Game Backend - User Service
Business logic for user management
"""
import logging
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_password_hash, verify_password
from src.modules.user.models import User
from src.modules.user.repository import UserRepository
from src.modules.user.exceptions import (
    UserNotFoundError,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    InvalidUserDataError
)

logger = logging.getLogger(__name__)


class UserService:
    """Service class for user-related business logic"""
    
    def __init__(self):
        self.repository = UserRepository()
    
    async def create_user(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        nickname: str
    ) -> User:
        """
        Create a new registered user
        
        Args:
            db: Database session
            email: User email
            password: Plain text password
            nickname: Display name
            
        Returns:
            Created user
            
        Raises:
            UserAlreadyExistsError: If email already exists
        """
        # Check if email already exists
        existing = await self.repository.get_by_email(db, email)
        if existing:
            raise UserAlreadyExistsError(f"User with email {email} already exists")
        
        # Hash password
        password_hash = get_password_hash(password)
        
        # Create user
        user = await self.repository.create(
            db=db,
            email=email,
            password_hash=password_hash,
            nickname=nickname,
            is_guest=False
        )
        
        logger.info(f"Created registered user: {user.id}")
        return user
    
    async def create_guest_user(
        self,
        db: AsyncSession,
        nickname: str
    ) -> User:
        """
        Create a guest user
        
        Args:
            db: Database session
            nickname: Display name
            
        Returns:
            Created guest user
        """
        # Generate unique guest identifier
        import random
        guest_suffix = f"{random.randint(1000, 9999)}"
        unique_nickname = f"{nickname}#{guest_suffix}"
        
        # Create guest user
        user = await self.repository.create(
            db=db,
            email=None,
            password_hash=None,
            nickname=unique_nickname,
            is_guest=True
        )
        
        logger.info(f"Created guest user: {user.id}")
        return user
    
    async def get_user(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            User or None
        """
        return await self.repository.get_by_id(db, user_id)
    
    async def get_user_by_email(
        self,
        db: AsyncSession,
        email: str
    ) -> Optional[User]:
        """
        Get user by email
        
        Args:
            db: Database session
            email: User email
            
        Returns:
            User or None
        """
        return await self.repository.get_by_email(db, email)
    
    async def authenticate_user(
        self,
        db: AsyncSession,
        email: str,
        password: str
    ) -> User:
        """
        Authenticate user with email and password
        
        Args:
            db: Database session
            email: User email
            password: Plain text password
            
        Returns:
            Authenticated user
            
        Raises:
            InvalidCredentialsError: If authentication fails
        """
        user = await self.get_user_by_email(db, email)
        if not user:
            raise InvalidCredentialsError("Invalid email or password")
        
        if not user.password_hash:
            raise InvalidCredentialsError("Invalid email or password")
        
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")
        
        if not user.is_active:
            raise InvalidCredentialsError("User account is inactive")
        
        # Update last login
        await self.repository.update_last_login(db, user)
        
        return user
    
    async def convert_guest_to_registered(
        self,
        db: AsyncSession,
        user_id: UUID,
        email: str,
        password: str
    ) -> User:
        """
        Convert a guest user to registered user
        
        Args:
            db: Database session
            user_id: Guest user ID
            email: Email for the account
            password: Password for the account
            
        Returns:
            Updated user
            
        Raises:
            UserNotFoundError: If user not found
            InvalidUserDataError: If user is not guest
            UserAlreadyExistsError: If email already exists
        """
        # Get user
        user = await self.get_user(db, user_id)
        if not user:
            raise UserNotFoundError("User not found")
        
        if not user.is_guest:
            raise InvalidUserDataError("User is already registered")
        
        # Check if email exists
        existing = await self.repository.get_by_email(db, email)
        if existing:
            raise UserAlreadyExistsError(f"Email {email} is already in use")
        
        # Hash password
        password_hash = get_password_hash(password)
        
        # Update user
        updated_user = await self.repository.update(
            db=db,
            user=user,
            email=email,
            password_hash=password_hash,
            is_guest=False
        )
        
        logger.info(f"Converted guest user {user_id} to registered")
        return updated_user
    
    async def update_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        **kwargs
    ) -> User:
        """
        Update user information
        
        Args:
            db: Database session
            user_id: User ID
            **kwargs: Fields to update
            
        Returns:
            Updated user
            
        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.get_user(db, user_id)
        if not user:
            raise UserNotFoundError("User not found")
        
        # Don't allow certain fields to be updated directly
        kwargs.pop('id', None)
        kwargs.pop('is_guest', None)
        kwargs.pop('created_at', None)
        
        # Update user
        updated_user = await self.repository.update(db, user, **kwargs)
        
        logger.info(f"Updated user: {user_id}")
        return updated_user
    
    async def update_password(
        self,
        db: AsyncSession,
        user_id: UUID,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Update user password
        
        Args:
            db: Database session
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Returns:
            True if updated successfully
            
        Raises:
            UserNotFoundError: If user not found
            InvalidCredentialsError: If current password is wrong
        """
        user = await self.get_user(db, user_id)
        if not user:
            raise UserNotFoundError("User not found")
        
        if user.is_guest:
            raise InvalidUserDataError("Guest users cannot have passwords")
        
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")
        
        # Hash new password
        new_password_hash = get_password_hash(new_password)
        
        # Update password
        await self.repository.update(db, user, password_hash=new_password_hash)
        
        logger.info(f"Updated password for user: {user_id}")
        return True
    
    async def get_user_stats(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> dict:
        """
        Get user statistics
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            User statistics dictionary
        """
        user = await self.get_user(db, user_id)
        if not user:
            raise UserNotFoundError("User not found")
        
        stats = {
            "user_id": user_id,
            "account_type": "guest" if user.is_guest else "registered",
            "member_since": user.created_at,
            "competitions_created": await self.repository.get_competitions_created_count(db, user_id),
            "sessions_organized": await self.repository.get_sessions_organized_count(db, user_id),
            "sessions_played": await self.repository.get_sessions_played_count(db, user_id),
            "total_votes_cast": await self.repository.get_total_votes_count(db, user_id)
        }
        
        return stats
    
    async def get_user_competitions(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[dict], int]:
        """
        Get competitions created by user
        
        Args:
            db: Database session
            user_id: User ID
            skip: Pagination offset
            limit: Pagination limit
            
        Returns:
            Tuple of (competitions, total_count)
        """
        return await self.repository.get_user_competitions(db, user_id, skip, limit)
    
    async def get_user_sessions(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[dict], int]:
        """
        Get sessions participated by user
        
        Args:
            db: Database session
            user_id: User ID
            skip: Pagination offset
            limit: Pagination limit
            
        Returns:
            Tuple of (sessions, total_count)
        """
        return await self.repository.get_user_sessions(db, user_id, skip, limit)
    
    async def deactivate_user(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> bool:
        """
        Deactivate a user account
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            True if deactivated successfully
        """
        user = await self.get_user(db, user_id)
        if not user:
            raise UserNotFoundError("User not found")
        
        await self.repository.update(db, user, is_active=False)
        
        logger.info(f"Deactivated user: {user_id}")
        return True
    
    async def delete_guest_user(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> bool:
        """
        Delete a guest user account
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            True if deleted successfully
            
        Raises:
            InvalidUserDataError: If user is not guest
        """
        user = await self.get_user(db, user_id)
        if not user:
            raise UserNotFoundError("User not found")
        
        if not user.is_guest:
            raise InvalidUserDataError("Only guest accounts can be deleted")
        
        await self.repository.delete(db, user)
        
        logger.info(f"Deleted guest user: {user_id}")
        return True


# Create service instance
user_service = UserService()


# Convenience functions for direct import
async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    nickname: str
) -> User:
    return await user_service.create_user(db, email, password, nickname)

async def create_guest_user(db: AsyncSession, nickname: str) -> User:
    return await user_service.create_guest_user(db, nickname)

async def get_user(db: AsyncSession, user_id: UUID) -> Optional[User]:
    return await user_service.get_user(db, user_id)

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    return await user_service.get_user_by_email(db, email)

async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    return await user_service.authenticate_user(db, email, password)

async def convert_guest_to_registered(
    db: AsyncSession,
    user_id: UUID,
    email: str,
    password: str
) -> User:
    return await user_service.convert_guest_to_registered(db, user_id, email, password)
