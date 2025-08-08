"""
Tournament Game Backend - Session Repository
Data access layer for session entities
"""
import logging
from typing import List, Optional, Tuple
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from src.modules.session.models import GameSession, SessionPlayer, Vote, SessionRound

logger = logging.getLogger(__name__)


class SessionRepository:
    """Repository class for session data access"""
    
    async def create(
        self,
        db: AsyncSession,
        code: str,
        competition_id: UUID,
        organizer_id: Optional[UUID] = None,
        organizer_name: str = "Organizer"
    ) -> GameSession:
        """
        Create a new game session
        
        Args:
            db: Database session
            code: Unique session code
            competition_id: Competition ID
            organizer_id: User ID of organizer
            organizer_name: Display name of organizer
            
        Returns:
            Created game session
        """
        session = GameSession(
            code=code,
            competition_id=competition_id,
            organizer_id=organizer_id,
            organizer_name=organizer_name,
            status="waiting"
        )
        
        db.add(session)
        await db.flush()
        await db.refresh(session)
        
        return session
    
    async def get_by_id(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> Optional[GameSession]:
        """
        Get session by ID
        
        Args:
            db: Database session
            session_id: Session ID
            
        Returns:
            Session or None
        """
        query = select(GameSession).where(GameSession.id == session_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_code(
        self,
        db: AsyncSession,
        code: str
    ) -> Optional[GameSession]:
        """
        Get session by code
        
        Args:
            db: Database session
            code: Session code
            
        Returns:
            Session or None
        """
        query = select(GameSession).where(GameSession.code == code)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_with_players(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> Optional[GameSession]:
        """
        Get session with players loaded
        
        Args:
            db: Database session
            session_id: Session ID
            
        Returns:
            Session with players or None
        """
        query = (
            select(GameSession)
            .options(selectinload(GameSession.players))
            .where(GameSession.id == session_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_paginated(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        competition_id: Optional[UUID] = None,
        organizer_id: Optional[UUID] = None
    ) -> Tuple[List[GameSession], int]:
        """
        Get paginated list of sessions
        
        Args:
            db: Database session
            skip: Number to skip
            limit: Number to return
            status: Filter by status
            competition_id: Filter by competition
            organizer_id: Filter by organizer
            
        Returns:
            Tuple of (sessions, total_count)
        """
        # Base query
        query = select(GameSession)
        count_query = select(func.count()).select_from(GameSession)
        
        # Apply filters
        if status:
            query = query.where(GameSession.status == status)
            count_query = count_query.where(GameSession.status == status)
        
        if competition_id:
            query = query.where(GameSession.competition_id == competition_id)
            count_query = count_query.where(GameSession.competition_id == competition_id)
        
        if organizer_id:
            query = query.where(GameSession.organizer_id == organizer_id)
            count_query = count_query.where(GameSession.organizer_id == organizer_id)
        
        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply ordering and pagination
        query = query.order_by(GameSession.created_at.desc())
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        sessions = list(result.scalars().all())
        
        return sessions, total
    
    async def update(
        self,
        db: AsyncSession,
        session: GameSession,
        **kwargs
    ) -> GameSession:
        """
        Update a session
        
        Args:
            db: Database session
            session: Session to update
            **kwargs: Fields to update
            
        Returns:
            Updated session
        """
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        session.updated_at = datetime.utcnow()
        
        await db.flush()
        await db.refresh(session)
        
        return session
    
    async def delete(
        self,
        db: AsyncSession,
        session: GameSession
    ) -> bool:
        """
        Delete a session
        
        Args:
            db: Database session
            session: Session to delete
            
        Returns:
            True if deleted
        """
        await db.delete(session)
        await db.flush()
        return True
    
    # Player methods
    
    async def add_player(
        self,
        db: AsyncSession,
        session_id: UUID,
        user_id: Optional[UUID],
        nickname: str,
        is_organizer: bool = False
    ) -> SessionPlayer:
        """
        Add a player to session
        
        Args:
            db: Database session
            session_id: Session ID
            user_id: User ID (optional)
            nickname: Player nickname
            is_organizer: Whether player is organizer
            
        Returns:
            Created player
        """
        player = SessionPlayer(
            session_id=session_id,
            user_id=user_id,
            nickname=nickname,
            is_organizer=is_organizer
        )
        
        db.add(player)
        await db.flush()
        await db.refresh(player)
        
        return player
    
    async def get_player(
        self,
        db: AsyncSession,
        player_id: UUID
    ) -> Optional[SessionPlayer]:
        """Get player by ID"""
        query = select(SessionPlayer).where(SessionPlayer.id == player_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_player_by_user_id(
        self,
        db: AsyncSession,
        session_id: UUID,
        user_id: UUID
    ) -> Optional[SessionPlayer]:
        """Get player by user ID in session"""
        query = select(SessionPlayer).where(
            and_(
                SessionPlayer.session_id == session_id,
                SessionPlayer.user_id == user_id
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_players(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> List[SessionPlayer]:
        """Get all players in session"""
        query = (
            select(SessionPlayer)
            .where(SessionPlayer.session_id == session_id)
            .order_by(SessionPlayer.joined_at)
        )
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_player_count(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> int:
        """Get count of players in session"""
        query = (
            select(func.count())
            .select_from(SessionPlayer)
            .where(SessionPlayer.session_id == session_id)
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    # Vote methods
    
    async def create_vote(
        self,
        db: AsyncSession,
        session_id: UUID,
        player_id: UUID,
        item_id: UUID,
        round_number: int,
        pair_index: int,
        weight: float = 1.0
    ) -> Vote:
        """Create a vote"""
        vote = Vote(
            session_id=session_id,
            player_id=player_id,
            item_id=item_id,
            round_number=round_number,
            pair_index=pair_index,
            weight=weight
        )
        
        db.add(vote)
        await db.flush()
        await db.refresh(vote)
        
        return vote
    
    async def get_votes_for_pair(
        self,
        db: AsyncSession,
        session_id: UUID,
        round_number: int,
        pair_index: int
    ) -> List[Vote]:
        """Get all votes for a specific pair"""
        query = select(Vote).where(
            and_(
                Vote.session_id == session_id,
                Vote.round_number == round_number,
                Vote.pair_index == pair_index
            )
        )
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_player_votes(
        self,
        db: AsyncSession,
        session_id: UUID,
        player_id: UUID
    ) -> List[Vote]:
        """Get all votes by a player in session"""
        query = select(Vote).where(
            and_(
                Vote.session_id == session_id,
                Vote.player_id == player_id
            )
        ).order_by(Vote.created_at)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_total_votes(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> int:
        """Get total number of votes in session"""
        query = (
            select(func.count())
            .select_from(Vote)
            .where(Vote.session_id == session_id)
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    # Round methods
    
    async def create_round(
        self,
        db: AsyncSession,
        session_id: UUID,
        round_number: int,
        round_data: dict
    ) -> SessionRound:
        """Create a session round"""
        session_round = SessionRound(
            session_id=session_id,
            round_number=round_number,
            round_data=round_data,
            status="in_progress"
        )
        
        db.add(session_round)
        await db.flush()
        await db.refresh(session_round)
        
        return session_round
    
    async def get_round(
        self,
        db: AsyncSession,
        session_id: UUID,
        round_number: int
    ) -> Optional[SessionRound]:
        """Get specific round"""
        query = select(SessionRound).where(
            and_(
                SessionRound.session_id == session_id,
                SessionRound.round_number == round_number
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_rounds(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> List[SessionRound]:
        """Get all rounds for session"""
        query = (
            select(SessionRound)
            .where(SessionRound.session_id == session_id)
            .order_by(SessionRound.round_number)
        )
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def update_round(
        self,
        db: AsyncSession,
        session_round: SessionRound,
        **kwargs
    ) -> SessionRound:
        """Update a round"""
        for key, value in kwargs.items():
            if hasattr(session_round, key):
                setattr(session_round, key, value)
        
        await db.flush()
        await db.refresh(session_round)
        
        return session_round
    
    # Aggregate methods
    
    async def get_active_session_count(
        self,
        db: AsyncSession,
        competition_id: Optional[UUID] = None
    ) -> int:
        """Get count of active sessions"""
        query = (
            select(func.count())
            .select_from(GameSession)
            .where(GameSession.status.in_(["waiting", "in_progress"]))
        )
        
        if competition_id:
            query = query.where(GameSession.competition_id == competition_id)
        
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def get_completed_session_count(
        self,
        db: AsyncSession,
        competition_id: Optional[UUID] = None
    ) -> int:
        """Get count of completed sessions"""
        query = (
            select(func.count())
            .select_from(GameSession)
            .where(GameSession.status == "completed")
        )
        
        if competition_id:
            query = query.where(GameSession.competition_id == competition_id)
        
        result = await db.execute(query)
        return result.scalar() or 0
