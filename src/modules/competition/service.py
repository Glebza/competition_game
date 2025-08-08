"""
Tournament Game Backend - Competition Service
Business logic for competition management
"""
import logging
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.competition.models import Competition, CompetitionItem
from src.modules.competition.repository import CompetitionRepository
from src.modules.competition.exceptions import (
    CompetitionNotFoundError,
    CompetitionItemNotFoundError,
    CompetitionItemLimitError,
    InvalidCompetitionDataError,
    DuplicateCompetitionError
)
from src.config import settings

logger = logging.getLogger(__name__)


class CompetitionService:
    """Service class for competition-related business logic"""
    
    def __init__(self):
        self.repository = CompetitionRepository()
    
    async def create_competition(
        self,
        db: AsyncSession,
        competition_data: dict,
        created_by: Optional[UUID] = None
    ) -> Competition:
        """
        Create a new competition
        
        Args:
            db: Database session
            competition_data: Competition data
            created_by: User ID of creator
            
        Returns:
            Created competition
            
        Raises:
            InvalidCompetitionDataError: If data is invalid
        """
        # Validate competition data
        if not competition_data.get("name"):
            raise InvalidCompetitionDataError("Competition name is required")
        
        if len(competition_data["name"]) > 255:
            raise InvalidCompetitionDataError("Competition name too long (max 255 characters)")
        
        # Check for duplicate name (optional for MVP)
        existing = await self.repository.get_by_name(db, competition_data["name"])
        if existing:
            raise DuplicateCompetitionError(f"Competition with name '{competition_data['name']}' already exists")
        
        # Create competition
        competition = await self.repository.create(
            db,
            name=competition_data["name"],
            description=competition_data.get("description"),
            created_by=created_by
        )
        
        logger.info(f"Created competition: {competition.id}")
        return competition
    
    async def get_competition(self, db: AsyncSession, competition_id: UUID) -> Competition:
        """
        Get competition by ID
        
        Args:
            db: Database session
            competition_id: Competition ID
            
        Returns:
            Competition object
            
        Raises:
            CompetitionNotFoundError: If competition not found
        """
        competition = await self.repository.get_by_id(db, competition_id)
        if not competition:
            raise CompetitionNotFoundError(f"Competition {competition_id} not found")
        
        return competition
    
    async def get_competition_with_items(
        self,
        db: AsyncSession,
        competition_id: UUID
    ) -> Dict[str, Any]:
        """
        Get competition with all its items
        
        Args:
            db: Database session
            competition_id: Competition ID
            
        Returns:
            Competition with items
        """
        competition = await self.repository.get_with_items(db, competition_id)
        if not competition:
            raise CompetitionNotFoundError(f"Competition {competition_id} not found")
        
        # Calculate additional info
        item_count = len(competition.items)
        can_start_session = item_count >= settings.MIN_ITEMS_PER_COMPETITION
        
        return {
            "id": competition.id,
            "name": competition.name,
            "description": competition.description,
            "created_by": competition.created_by,
            "created_at": competition.created_at,
            "updated_at": competition.updated_at,
            "item_count": item_count,
            "session_count": await self.repository.get_session_count(db, competition_id),
            "items": sorted(competition.items, key=lambda x: x.order_index),
            "can_start_session": can_start_session
        }
    
    async def get_competitions(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        created_by: Optional[UUID] = None
    ) -> Tuple[List[Competition], int]:
        """
        Get paginated list of competitions
        
        Args:
            db: Database session
            skip: Number of items to skip
            limit: Number of items to return
            search: Search term for name/description
            created_by: Filter by creator
            
        Returns:
            Tuple of (competitions, total_count)
        """
        competitions, total = await self.repository.get_paginated(
            db,
            skip=skip,
            limit=limit,
            search=search,
            created_by=created_by
        )
        
        # Add item counts
        for comp in competitions:
            comp.item_count = await self.repository.get_item_count(db, comp.id)
            comp.session_count = await self.repository.get_session_count(db, comp.id)
        
        return competitions, total
    
    async def update_competition(
        self,
        db: AsyncSession,
        competition_id: UUID,
        competition_update: dict
    ) -> Competition:
        """
        Update competition details
        
        Args:
            db: Database session
            competition_id: Competition ID
            competition_update: Update data
            
        Returns:
            Updated competition
        """
        competition = await self.get_competition(db, competition_id)
        
        # Validate update data
        if "name" in competition_update and len(competition_update["name"]) > 255:
            raise InvalidCompetitionDataError("Competition name too long (max 255 characters)")
        
        # Update competition
        updated = await self.repository.update(
            db,
            competition,
            **competition_update
        )
        
        logger.info(f"Updated competition: {competition_id}")
        return updated
    
    async def delete_competition(self, db: AsyncSession, competition_id: UUID) -> bool:
        """
        Delete a competition
        
        Args:
            db: Database session
            competition_id: Competition ID
            
        Returns:
            True if deleted successfully
        """
        competition = await self.get_competition(db, competition_id)
        
        # Check if competition has active sessions
        session_count = await self.repository.get_active_session_count(db, competition_id)
        if session_count > 0:
            raise InvalidCompetitionDataError(
                f"Cannot delete competition with {session_count} active sessions"
            )
        
        # Delete competition (cascade will delete items)
        await self.repository.delete(db, competition)
        
        logger.info(f"Deleted competition: {competition_id}")
        return True
    
    async def add_competition_item(
        self,
        db: AsyncSession,
        competition_id: UUID,
        name: str,
        image_url: str,
        order_index: Optional[int] = None
    ) -> CompetitionItem:
        """
        Add an item to a competition
        
        Args:
            db: Database session
            competition_id: Competition ID
            name: Item name
            image_url: URL of item image
            order_index: Optional order index
            
        Returns:
            Created competition item
        """
        # Check competition exists
        competition = await self.get_competition(db, competition_id)
        
        # Check item limit
        current_count = await self.repository.get_item_count(db, competition_id)
        if current_count >= settings.MAX_ITEMS_PER_COMPETITION:
            raise CompetitionItemLimitError(
                f"Competition already has maximum {settings.MAX_ITEMS_PER_COMPETITION} items"
            )
        
        # Set order index if not provided
        if order_index is None:
            order_index = current_count
        
        # Create item
        item = await self.repository.create_item(
            db,
            competition_id=competition_id,
            name=name,
            image_url=image_url,
            order_index=order_index
        )
        
        logger.info(f"Added item to competition {competition_id}: {item.id}")
        return item
    
    async def delete_competition_item(
        self,
        db: AsyncSession,
        competition_id: UUID,
        item_id: UUID
    ) -> bool:
        """
        Delete an item from a competition
        
        Args:
            db: Database session
            competition_id: Competition ID
            item_id: Item ID
            
        Returns:
            True if deleted successfully
        """
        # Verify competition and item
        competition = await self.get_competition(db, competition_id)
        item = await self.repository.get_item_by_id(db, item_id)
        
        if not item or item.competition_id != competition_id:
            raise CompetitionItemNotFoundError(f"Item {item_id} not found in competition")
        
        # Check minimum items
        current_count = await self.repository.get_item_count(db, competition_id)
        if current_count <= settings.MIN_ITEMS_PER_COMPETITION:
            raise InvalidCompetitionDataError(
                f"Competition must have at least {settings.MIN_ITEMS_PER_COMPETITION} items"
            )
        
        # Delete item
        await self.repository.delete_item(db, item)
        
        # Reorder remaining items
        await self._reorder_items(db, competition_id)
        
        logger.info(f"Deleted item {item_id} from competition {competition_id}")
        return True
    
    async def duplicate_competition(
        self,
        db: AsyncSession,
        competition_id: UUID,
        new_name: str,
        created_by: Optional[UUID] = None
    ) -> Competition:
        """
        Create a copy of an existing competition
        
        Args:
            db: Database session
            competition_id: Source competition ID
            new_name: Name for the new competition
            created_by: User creating the duplicate
            
        Returns:
            New competition
        """
        # Get source competition with items
        source = await self.repository.get_with_items(db, competition_id)
        if not source:
            raise CompetitionNotFoundError(f"Competition {competition_id} not found")
        
        # Create new competition
        new_competition = await self.create_competition(
            db,
            {"name": new_name, "description": f"Copy of: {source.description or source.name}"},
            created_by
        )
        
        # Copy items
        for item in source.items:
            await self.add_competition_item(
                db,
                new_competition.id,
                item.name,
                item.image_url,
                item.order_index
            )
        
        logger.info(f"Duplicated competition {competition_id} to {new_competition.id}")
        return new_competition
    
    async def _reorder_items(self, db: AsyncSession, competition_id: UUID):
        """Reorder items after deletion to maintain sequence"""
        items = await self.repository.get_items(db, competition_id)
        
        for index, item in enumerate(sorted(items, key=lambda x: x.order_index)):
            if item.order_index != index:
                item.order_index = index
                await self.repository.update_item(db, item)
    
    async def get_items_by_ids(
        self,
        db: AsyncSession,
        item_ids: List[UUID]
    ) -> List[CompetitionItem]:
        """Get multiple items by their IDs"""
        return await self.repository.get_items_by_ids(db, item_ids)
    
    async def get_item_by_id(
        self,
        db: AsyncSession,
        item_id: UUID
    ) -> Optional[CompetitionItem]:
        """Get a single item by ID"""
        return await self.repository.get_item_by_id(db, item_id)


# Create service instance
competition_service = CompetitionService()


# Convenience functions for direct import
async def create_competition(db: AsyncSession, competition_data: dict, created_by: Optional[UUID] = None) -> Competition:
    return await competition_service.create_competition(db, competition_data, created_by)

async def get_competition(db: AsyncSession, competition_id: UUID) -> Competition:
    return await competition_service.get_competition(db, competition_id)

async def get_competition_with_items(db: AsyncSession, competition_id: UUID) -> Dict[str, Any]:
    return await competition_service.get_competition_with_items(db, competition_id)

async def get_competitions(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    created_by: Optional[UUID] = None
) -> Tuple[List[Competition], int]:
    return await competition_service.get_competitions(db, skip, limit, search, created_by)

async def update_competition(db: AsyncSession, competition_id: UUID, competition_update: dict) -> Competition:
    return await competition_service.update_competition(db, competition_id, competition_update)

async def delete_competition(db: AsyncSession, competition_id: UUID) -> bool:
    return await competition_service.delete_competition(db, competition_id)

async def add_competition_item(
    db: AsyncSession,
    competition_id: UUID,
    name: str,
    image_url: str,
    order_index: Optional[int] = None
) -> CompetitionItem:
    return await competition_service.add_competition_item(db, competition_id, name, image_url, order_index)

async def delete_competition_item(db: AsyncSession, competition_id: UUID, item_id: UUID) -> bool:
    return await competition_service.delete_competition_item(db, competition_id, item_id)

async def duplicate_competition(
    db: AsyncSession,
    competition_id: UUID,
    new_name: str,
    created_by: Optional[UUID] = None
) -> Competition:
    return await competition_service.duplicate_competition(db, competition_id, new_name, created_by)
