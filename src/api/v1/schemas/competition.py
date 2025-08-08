"""
Tournament Game Backend - Competition Schemas
Pydantic models for competition-related endpoints
"""
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.api.v1.schemas.common import BaseSchema, TimestampMixin, PaginatedResponse


class CompetitionItemBase(BaseSchema):
    """Base schema for competition items"""
    name: str = Field(..., min_length=1, max_length=255, description="Item name")
    image_url: str = Field(..., description="URL of the item image")


class CompetitionItemCreate(CompetitionItemBase):
    """Schema for creating a competition item"""
    order_index: Optional[int] = Field(None, description="Order of the item in the competition")


class CompetitionItemUpdate(BaseSchema):
    """Schema for updating a competition item"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    image_url: Optional[str] = None
    order_index: Optional[int] = None


class CompetitionItemResponse(CompetitionItemBase, TimestampMixin):
    """Schema for competition item response"""
    id: UUID
    competition_id: UUID
    order_index: int
    
    class Config:
        from_attributes = True


class CompetitionBase(BaseSchema):
    """Base schema for competitions"""
    name: str = Field(..., min_length=1, max_length=255, description="Competition name")
    description: Optional[str] = Field(None, max_length=1000, description="Competition description")


class CompetitionCreate(CompetitionBase):
    """Schema for creating a competition"""
    pass


class CompetitionUpdate(BaseSchema):
    """Schema for updating a competition"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class CompetitionResponse(CompetitionBase, TimestampMixin):
    """Schema for competition response"""
    id: UUID
    created_by: Optional[UUID] = Field(None, description="ID of the user who created the competition")
    item_count: int = Field(0, description="Number of items in the competition")
    session_count: int = Field(0, description="Number of game sessions for this competition")
    
    class Config:
        from_attributes = True


class CompetitionDetailResponse(CompetitionResponse):
    """Detailed competition response with items"""
    items: List[CompetitionItemResponse] = Field(default_factory=list, description="Competition items")
    can_start_session: bool = Field(True, description="Whether a game session can be started")
    
    @field_validator('can_start_session', mode='before')
    @classmethod
    def validate_can_start(cls, v, info):
        """Check if competition has enough items to start a session"""
        data = info.data
        items = data.get('items', [])
        return len(items) >= 4  # Minimum 4 items required


class CompetitionListResponse(PaginatedResponse[CompetitionResponse]):
    """Paginated list of competitions"""
    pass


class CompetitionStats(BaseSchema):
    """Competition statistics"""
    total_competitions: int
    total_items: int
    total_sessions: int
    most_popular_competition_id: Optional[UUID] = None
    most_popular_competition_name: Optional[str] = None
    most_popular_competition_sessions: int = 0


class CompetitionDuplicateRequest(BaseSchema):
    """Request to duplicate a competition"""
    new_name: str = Field(..., min_length=1, max_length=255, description="Name for the duplicated competition")
    include_items: bool = Field(True, description="Whether to copy items to the new competition")


class CompetitionImportRequest(BaseSchema):
    """Request to import a competition from external source"""
    source_type: str = Field(..., pattern="^(json|csv|url)$", description="Import source type")
    source_data: str = Field(..., description="Source data (JSON string, CSV content, or URL)")
    name: str = Field(..., min_length=1, max_length=255, description="Competition name")
    description: Optional[str] = Field(None, max_length=1000)


class CompetitionExportResponse(BaseSchema):
    """Response for competition export"""
    format: str = Field(..., pattern="^(json|csv)$", description="Export format")
    data: str = Field(..., description="Exported data")
    filename: str = Field(..., description="Suggested filename for download")


class BulkItemsUploadRequest(BaseSchema):
    """Request for bulk items upload"""
    items: List[CompetitionItemCreate] = Field(..., min_items=1, max_items=128)
    
    @field_validator('items')
    @classmethod
    def validate_unique_names(cls, v):
        """Ensure item names are unique"""
        names = [item.name for item in v]
        if len(names) != len(set(names)):
            raise ValueError("Item names must be unique")
        return v


class CompetitionSearchParams(BaseSchema):
    """Search parameters for competitions"""
    search: Optional[str] = Field(None, description="Search in name and description")
    created_by: Optional[UUID] = Field(None, description="Filter by creator")
    min_items: Optional[int] = Field(None, ge=0, description="Minimum number of items")
    max_items: Optional[int] = Field(None, ge=0, description="Maximum number of items")
    has_sessions: Optional[bool] = Field(None, description="Filter competitions with/without sessions")
    order_by: str = Field("created_at", pattern="^(created_at|name|item_count|session_count)$")
    order_dir: str = Field("desc", pattern="^(asc|desc)$")
