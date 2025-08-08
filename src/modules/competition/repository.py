"""
Tournament Game Backend - Competition Repository
Data access layer for competition entities
"""
import logging
from typing import List, Optional, Tuple
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, func, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.competition.models import Competition, CompetitionItem
from src.modules.session.models import GameSession

logger = logging.getLogger(__name__)


class CompetitionRepository:
    """Repository class for competition data access"""
    
    async def create(
        self,
        db: AsyncSession,
        name: str,
        description: Optional[str] = None,
        created_by: Optional[UUID] = None
    ) -> Competition:
        """
        Create a new competition
        
        Args:
            db: Database session
            name: Competition name
            description: Competition description
            created_by: User ID of creator
            
        Returns:
            Created competition
        """
        competition = Competition(
            name=name,
            description=description,
            created_by=created_by
        )
        
        db.add(competition)
        await db.flush()
        await db.refresh(competition)
        
        return competition
    
    async def get_by_id(
        self,
        db: AsyncSession,
        competition_id: UUID
    ) -> Optional[Competition]:
        """
        Get competition by ID
        
        Args:
            db: Database session
            competition_id: Competition ID
            
        Returns:
            Competition or None
        """
        query = select(Competition).where(Competition.id == competition_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_name(
        self,
        db: AsyncSession,
        name: str
    ) -> Optional[Competition]:
        """
        Get competition by name
        
        Args:
            db: Database session
            name: Competition name
            
        Returns:
            Competition or None
        """
        query = select(Competition).where(Competition.name == name)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_with_items(
        self,
        db: AsyncSession,
        competition_id: UUID
    ) -> Optional[Competition]:
        """
        Get competition with all its items
        
        Args:
            db: Database session
            competition_id: Competition ID
            
        Returns:
            Competition with items loaded or None
        """
        query = (
            select(Competition)
            .options(selectinload(Competition.items))
            .where(Competition.id == competition_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_paginated(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        created_by: Optional[UUID] = None,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[Competition], int]:
        """
        Get paginated list of competitions
        
        Args:
            db: Database session
            skip: Number of items to skip
            limit: Number of items to return
            search: Search term for name/description
            created_by: Filter by creator
            order_by: Field to order by
            order_desc: Order descending
            
        Returns:
            Tuple of (competitions, total_count)
        """
        # Base query
        query = select(Competition)
        count_query = select(func.count()).select_from(Competition)
        
        # Apply filters
        if search:
            search_filter = or_(
                Competition.name.ilike(f"%{search}%"),
                Competition.description.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        if created_by:
            query = query.where(Competition.created_by == created_by)
            count_query = count_query.where(Competition.created_by == created_by)
        
        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply ordering
        order_column = getattr(Competition, order_by, Competition.created_at)
        if order_desc:
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        competitions = list(result.scalars().all())
        
        return competitions, total
    
    async def update(
        self,
        db: AsyncSession,
        competition: Competition,
        **kwargs
    ) -> Competition:
        """
        Update a competition
        
        Args:
            db: Database session
            competition: Competition to update
            **kwargs: Fields to update
            
        Returns:
            Updated competition
        """
        for key, value in kwargs.items():
            if hasattr(competition, key):
                setattr(competition, key, value)
        
        competition.updated_at = datetime.utcnow()
        
        await db.flush()
        await db.refresh(competition)
        
        return competition
    
    async def delete(
        self,
        db: AsyncSession,
        competition: Competition
    ) -> bool:
        """
        Delete a competition
        
        Args:
            db: Database session
            competition: Competition to delete
            
        Returns:
            True if deleted
        """
        await db.delete(competition)
        await db.flush()
        return True
    
    # Competition Item methods
    
    async def create_item(
        self,
        db: AsyncSession,
        competition_id: UUID,
        name: str,
        image_url: str,
        order_index: int = 0
    ) -> CompetitionItem:
        """
        Create a competition item
        
        Args:
            db: Database session
            competition_id: Competition ID
            name: Item name
            image_url: Item image URL
            order_index: Order index
            
        Returns:
            Created item
        """
        item = CompetitionItem(
            competition_id=competition_id,
            name=name,
            image_url=image_url,
            order_index=order_index
        )
        
        db.add(item)
        await db.flush()
        await db.refresh(item)
        
        return item
    
    async def get_item_by_id(
        self,
        db: AsyncSession,
        item_id: UUID
    ) -> Optional[CompetitionItem]:
        """
        Get item by ID
        
        Args:
            db: Database session
            item_id: Item ID
            
        Returns:
            Item or None
        """
        query = select(CompetitionItem).where(CompetitionItem.id == item_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_items(
        self,
        db: AsyncSession,
        competition_id: UUID
    ) -> List[CompetitionItem]:
        """
        Get all items for a competition
        
        Args:
            db: Database session
            competition_id: Competition ID
            
        Returns:
            List of items
        """
        query = (
            select(CompetitionItem)
            .where(CompetitionItem.competition_id == competition_id)
            .order_by(CompetitionItem.order_index)
        )
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_items_by_ids(
        self,
        db: AsyncSession,
        item_ids: List[UUID]
    ) -> List[CompetitionItem]:
        """
        Get multiple items by IDs
        
        Args:
            db: Database session
            item_ids: List of item IDs
            
        Returns:
            List of items
        """
        if not item_ids:
            return []
        
        query = select(CompetitionItem).where(CompetitionItem.id.in_(item_ids))
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def update_item(
        self,
        db: AsyncSession,
        item: CompetitionItem,
        **kwargs
    ) -> CompetitionItem:
        """
        Update an item
        
        Args:
            db: Database session
            item: Item to update
            **kwargs: Fields to update
            
        Returns:
            Updated item
        """
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        
        item.updated_at = datetime.utcnow()
        
        await db.flush()
        await db.refresh(item)
        
        return item
    
    async def delete_item(
        self,
        db: AsyncSession,
        item: CompetitionItem
    ) -> bool:
        """
        Delete an item
        
        Args:
            db: Database session
            item: Item to delete
            
        Returns:
            True if deleted
        """
        await db.delete(item)
        await db.flush()
        return True
    
    # Aggregate methods
    
    async def get_item_count(
        self,
        db: AsyncSession,
        competition_id: UUID
    ) -> int:
        """
        Get count of items in a competition
        
        Args:
            db: Database session
            competition_id: Competition ID
            
        Returns:
            Item count
        """
        query = (
            select(func.count())
            .select_from(CompetitionItem)
            .where(CompetitionItem.competition_id == competition_id)
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def get_session_count(
        self,
        db: AsyncSession,
        competition_id: UUID
    ) -> int:
        """
        Get count of sessions for a competition
        
        Args:
            db: Database session
            competition_id: Competition ID
            
        Returns:
            Session count
        """
        query = (
            select(func.count())
            .select_from(GameSession)
            .where(GameSession.competition_id == competition_id)
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def get_active_session_count(
        self,
        db: AsyncSession,
        competition_id: UUID
    ) -> int:
        """
        Get count of active sessions for a competition
        
        Args:
            db: Database session
            competition_id: Competition ID
            
        Returns:
            Active session count
        """
        query = (
            select(func.count())
            .select_from(GameSession)
            .where(
                and_(
                    GameSession.competition_id == competition_id,
                    GameSession.status.in_(["waiting", "in_progress"])
                )
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0
