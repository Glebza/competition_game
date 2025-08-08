"""
Tournament Game Backend - User Repository
Data access layer for user entities
"""
import logging
from typing import List, Optional, Tuple
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.user.models import User
from src.modules.competition.models import Competition
from src.modules.session.models import GameSession, SessionPlayer

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository class for user data access"""
    
    async def create(
        self,
        db: AsyncSession,
        email: Optional[str],
        password_hash: Optional[str],
        nickname: str,
        is_guest: bool = False
    ) -> User:
        """
        Create a new user
        
        Args:
            db: Database session
            email: User email (optional for guests)
            password_hash: Hashed password (optional for guests)
            nickname: Display name
            is_guest: Whether this is a guest user
            
        Returns:
            Created user
        """
        user = User(
            email=email,
            password_hash=password_hash,
            nickname=nickname,
            is_guest=is_guest,
            is_active=True
        )
        
        db.add(user)
        await db.flush()
        await db.refresh(user)
        
        return user
    
    async def get_by_id(
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
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_email(
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
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_nickname(
        self,
        db: AsyncSession,
        nickname: str
    ) -> Optional[User]:
        """
        Get user by nickname
        
        Args:
            db: Database session
            nickname: User nickname
            
        Returns:
            User or None
        """
        query = select(User).where(User.nickname == nickname)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def update(
        self,
        db: AsyncSession,
        user: User,
        **kwargs
    ) -> User:
        """
        Update a user
        
        Args:
            db: Database session
            user: User to update
            **kwargs: Fields to update
            
        Returns:
            Updated user
        """
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        
        await db.flush()
        await db.refresh(user)
        
        return user
    
    async def update_last_login(
        self,
        db: AsyncSession,
        user: User
    ) -> User:
        """
        Update user's last login time
        
        Args:
            db: Database session
            user: User to update
            
        Returns:
            Updated user
        """
        user.last_login = datetime.utcnow()
        await db.flush()
        await db.refresh(user)
        return user
    
    async def delete(
        self,
        db: AsyncSession,
        user: User
    ) -> bool:
        """
        Delete a user
        
        Args:
            db: Database session
            user: User to delete
            
        Returns:
            True if deleted
        """
        await db.delete(user)
        await db.flush()
        return True
    
    # Statistics methods
    
    async def get_competitions_created_count(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """
        Get count of competitions created by user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Competition count
        """
        query = (
            select(func.count())
            .select_from(Competition)
            .where(Competition.created_by == user_id)
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def get_sessions_organized_count(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """
        Get count of sessions organized by user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Session count
        """
        query = (
            select(func.count())
            .select_from(GameSession)
            .where(GameSession.organizer_id == user_id)
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def get_sessions_played_count(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """
        Get count of sessions played by user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Session count
        """
        query = (
            select(func.count(func.distinct(SessionPlayer.session_id)))
            .select_from(SessionPlayer)
            .where(SessionPlayer.user_id == user_id)
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def get_total_votes_count(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """
        Get total votes cast by user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Vote count
        """
        from src.modules.session.models import Vote
        
        query = (
            select(func.count())
            .select_from(Vote)
            .join(SessionPlayer, Vote.player_id == SessionPlayer.id)
            .where(SessionPlayer.user_id == user_id)
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    # Related data methods
    
    async def get_user_competitions(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Competition], int]:
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
        # Count query
        count_query = (
            select(func.count())
            .select_from(Competition)
            .where(Competition.created_by == user_id)
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Data query
        query = (
            select(Competition)
            .where(Competition.created_by == user_id)
            .order_by(Competition.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        competitions = list(result.scalars().all())
        
        return competitions, total
    
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
        # Base query for sessions where user is a player
        subquery = (
            select(SessionPlayer.session_id)
            .where(SessionPlayer.user_id == user_id)
            .subquery()
        )
        
        # Count query
        count_query = (
            select(func.count())
            .select_from(GameSession)
            .where(GameSession.id.in_(select(subquery.c.session_id)))
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Data query with joins
        query = (
            select(
                GameSession,
                SessionPlayer,
                Competition.name.label("competition_name")
            )
            .join(SessionPlayer, GameSession.id == SessionPlayer.session_id)
            .join(Competition, GameSession.competition_id == Competition.id)
            .where(SessionPlayer.user_id == user_id)
            .order_by(GameSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        
        # Format results
        sessions = []
        for row in result.all():
            session = row.GameSession
            player = row.SessionPlayer
            sessions.append({
                "id": session.id,
                "code": session.code,
                "competition_name": row.competition_name,
                "status": session.status,
                "created_at": session.created_at,
                "is_organizer": player.is_organizer,
                "player_nickname": player.nickname
            })
        
        return sessions, total
    
    # Aggregate queries
    
    async def get_active_users_count(
        self,
        db: AsyncSession,
        is_guest: Optional[bool] = None
    ) -> int:
        """
        Get count of active users
        
        Args:
            db: Database session
            is_guest: Filter by guest status
            
        Returns:
            User count
        """
        query = (
            select(func.count())
            .select_from(User)
            .where(User.is_active == True)
        )
        
        if is_guest is not None:
            query = query.where(User.is_guest == is_guest)
        
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def get_users_paginated(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        is_guest: Optional[bool] = None
    ) -> Tuple[List[User], int]:
        """
        Get paginated list of users
        
        Args:
            db: Database session
            skip: Pagination offset
            limit: Pagination limit
            search: Search term for nickname/email
            is_guest: Filter by guest status
            
        Returns:
            Tuple of (users, total_count)
        """
        # Base query
        query = select(User)
        count_query = select(func.count()).select_from(User)
        
        # Apply filters
        if search:
            search_filter = or_(
                User.nickname.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        if is_guest is not None:
            query = query.where(User.is_guest == is_guest)
            count_query = count_query.where(User.is_guest == is_guest)
        
        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply ordering and pagination
        query = query.order_by(User.created_at.desc())
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        users = list(result.scalars().all())
        
        return users, total
