"""
Tournament Game Backend - Media Schemas
Pydantic models for media-related operations
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.api.v1.schemas.common import BaseSchema, TimestampMixin


class MediaUploadResponse(BaseSchema):
    """Response after successful media upload"""
    url: str = Field(..., description="URL of the uploaded media")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., ge=0, description="File size in bytes")
    content_type: str = Field(..., description="MIME type of the file")
    thumbnail_url: Optional[str] = Field(None, description="URL of the thumbnail (if generated)")
    metadata: Optional[Dict[str, str]] = Field(None, description="Additional metadata")


class MediaBulkUploadItem(BaseSchema):
    """Individual item in bulk upload response"""
    url: str
    filename: str
    size: int
    content_type: str
    success: bool = True
    error: Optional[str] = None


class MediaBulkUploadResponse(BaseSchema):
    """Response for bulk media upload"""
    uploaded: List[MediaBulkUploadItem] = Field(..., description="Successfully uploaded files")
    failed: List[Dict[str, str]] = Field(..., description="Failed uploads with error messages")
    total_uploaded: int = Field(..., ge=0, description="Number of successfully uploaded files")
    total_failed: int = Field(..., ge=0, description="Number of failed uploads")
    
    @field_validator('total_uploaded', mode='before')
    @classmethod
    def validate_uploaded_count(cls, v, info):
        """Ensure uploaded count matches uploaded list length"""
        data = info.data
        uploaded = data.get('uploaded', [])
        return len(uploaded)
    
    @field_validator('total_failed', mode='before')
    @classmethod
    def validate_failed_count(cls, v, info):
        """Ensure failed count matches failed list length"""
        data = info.data
        failed = data.get('failed', [])
        return len(failed)


class MediaDeleteResponse(BaseSchema):
    """Response after media deletion"""
    success: bool
    message: str
    deleted_url: Optional[str] = None


class MediaInfo(BaseSchema, TimestampMixin):
    """Detailed media information"""
    id: UUID
    url: str
    filename: str
    size: int
    content_type: str
    folder: str
    uploaded_by: Optional[UUID] = None
    thumbnail_url: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    
    class Config:
        from_attributes = True


class PresignedUploadResponse(BaseSchema):
    """Response containing presigned upload URL"""
    upload_url: str = Field(..., description="Presigned URL for direct upload")
    file_url: str = Field(..., description="Final URL where file will be accessible")
    fields: Dict[str, str] = Field(..., description="Additional fields to include in upload")
    expires_at: datetime = Field(..., description="When the presigned URL expires")
    max_size: int = Field(..., description="Maximum allowed file size")


class ImageValidationResponse(BaseSchema):
    """Response for image URL validation"""
    valid: bool
    url: str
    error: Optional[str] = None
    dimensions: Optional[Dict[str, int]] = None  # {"width": 800, "height": 600}
    size: Optional[int] = None
    format: Optional[str] = None


class MediaUploadRequest(BaseSchema):
    """Request for media upload configuration"""
    folder: str = Field("general", description="Destination folder")
    generate_thumbnail: bool = Field(False, description="Whether to generate thumbnail")
    optimize: bool = Field(True, description="Whether to optimize image")
    max_width: Optional[int] = Field(None, gt=0, le=4096, description="Maximum width for resize")
    max_height: Optional[int] = Field(None, gt=0, le=4096, description="Maximum height for resize")
    quality: int = Field(85, ge=1, le=100, description="JPEG quality (1-100)")


class MediaSearchParams(BaseSchema):
    """Search parameters for media files"""
    folder: Optional[str] = Field(None, description="Filter by folder")
    uploaded_by: Optional[UUID] = Field(None, description="Filter by uploader")
    content_type: Optional[str] = Field(None, description="Filter by MIME type")
    min_size: Optional[int] = Field(None, ge=0, description="Minimum file size in bytes")
    max_size: Optional[int] = Field(None, ge=0, description="Maximum file size in bytes")
    filename_search: Optional[str] = Field(None, description="Search in filenames")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")


class MediaUsageStats(BaseSchema):
    """Media storage usage statistics"""
    total_files: int
    total_size_bytes: int
    total_size_mb: float
    by_folder: Dict[str, Dict[str, int]]  # folder -> {"count": n, "size": bytes}
    by_type: Dict[str, Dict[str, int]]  # content_type -> {"count": n, "size": bytes}
    
    @field_validator('total_size_mb', mode='before')
    @classmethod
    def calculate_size_mb(cls, v, info):
        """Convert bytes to MB"""
        data = info.data
        total_bytes = data.get('total_size_bytes', 0)
        return round(total_bytes / (1024 * 1024), 2)


class ThumbnailGenerationRequest(BaseSchema):
    """Request to generate thumbnail for existing image"""
    source_url: str = Field(..., description="URL of the source image")
    width: int = Field(400, gt=0, le=1200, description="Thumbnail width")
    height: int = Field(600, gt=0, le=1200, description="Thumbnail height")
    mode: str = Field("cover", pattern="^(cover|contain|stretch)$", description="Resize mode")


class ImageTransformRequest(BaseSchema):
    """Request to transform an image"""
    source_url: str = Field(..., description="URL of the source image")
    operations: List[Dict[str, Any]] = Field(..., description="List of operations to apply")
    output_format: Optional[str] = Field(None, pattern="^(jpeg|png|webp)$", description="Output format")
    output_quality: int = Field(85, ge=1, le=100, description="Output quality")
