"""
Tournament Game Backend - Media Service
Business logic for media/file management
"""
import logging
import os
import mimetypes
from typing import Optional, BinaryIO, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

import aiofiles
from fastapi import UploadFile

from src.config import settings
from src.core.storage import storage_client
from src.modules.media.exceptions import (
    FileUploadError,
    FileValidationError,
    FileSizeLimitError,
    FileNotFoundError
)

logger = logging.getLogger(__name__)


class MediaService:
    """Service class for media-related operations"""
    
    def __init__(self):
        self.storage = storage_client
        self.allowed_extensions = settings.ALLOWED_IMAGE_EXTENSIONS
        self.max_file_size = settings.MAX_UPLOAD_SIZE
    
    def validate_image_file(self, file: UploadFile) -> bool:
        """
        Validate if a file is an allowed image type
        
        Args:
            file: UploadFile object
            
        Returns:
            True if valid, False otherwise
        """
        # Check file extension
        if file.filename:
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in self.allowed_extensions:
                return False
        
        # Check content type
        if file.content_type:
            if not file.content_type.startswith('image/'):
                return False
            
            # Map content types to extensions
            content_type_map = {
                'image/jpeg': ['.jpg', '.jpeg'],
                'image/png': ['.png'],
                'image/webp': ['.webp']
            }
            
            allowed_types = [ct for ct, exts in content_type_map.items() 
                           if any(ext in self.allowed_extensions for ext in exts)]
            
            if file.content_type not in allowed_types:
                return False
        
        return True
    
    async def upload_image(
        self,
        file: UploadFile,
        folder: str = "general",
        user_id: Optional[UUID] = None
    ) -> str:
        """
        Upload an image file to storage
        
        Args:
            file: UploadFile object
            folder: Destination folder in storage
            user_id: User ID for tracking
            
        Returns:
            Public URL of the uploaded file
            
        Raises:
            FileValidationError: If file is invalid
            FileSizeLimitError: If file is too large
            FileUploadError: If upload fails
        """
        # Validate file
        if not self.validate_image_file(file):
            raise FileValidationError(
                f"Invalid file type. Allowed types: {', '.join(self.allowed_extensions)}"
            )
        
        # Check file size if available
        if file.size and file.size > self.max_file_size:
            raise FileSizeLimitError(
                f"File size ({file.size} bytes) exceeds maximum allowed size "
                f"({self.max_file_size} bytes)"
            )
        
        try:
            # Generate unique filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid4())[:8]
            ext = os.path.splitext(file.filename)[1].lower() if file.filename else '.jpg'
            
            # Sanitize folder name
            folder = folder.replace('.', '').replace('/', '')
            
            # Construct S3 key
            key = f"{folder}/{timestamp}_{unique_id}{ext}"
            
            # Read file content
            content = await file.read()
            
            # Reset file position for potential re-reading
            await file.seek(0)
            
            # Upload to storage
            import io
            file_obj = io.BytesIO(content)
            
            url = await self.storage.upload_file(
                file_content=file_obj,
                key=key,
                content_type=file.content_type,
                metadata={
                    "original_filename": file.filename or "unknown",
                    "uploaded_by": str(user_id) if user_id else "anonymous",
                    "upload_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Successfully uploaded image: {key}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to upload image: {e}")
            raise FileUploadError(f"Failed to upload file: {str(e)}")
    
    async def delete_image(
        self,
        file_key: str,
        user_id: Optional[UUID] = None
    ) -> bool:
        """
        Delete an image from storage
        
        Args:
            file_key: S3 key of the file
            user_id: User ID for tracking
            
        Returns:
            True if deleted successfully
        """
        try:
            success = await self.storage.delete_file(file_key)
            if success:
                logger.info(f"Deleted image: {file_key} by user {user_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to delete image {file_key}: {e}")
            return False
    
    def extract_key_from_url(self, url: str) -> Optional[str]:
        """
        Extract S3 key from a public URL
        
        Args:
            url: Public URL of the file
            
        Returns:
            S3 key or None
        """
        return self.storage.extract_key_from_url(url)
    
    async def generate_presigned_upload_url(
        self,
        filename: str,
        content_type: str,
        folder: str = "general",
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL for direct browser upload
        
        Args:
            filename: Original filename
            content_type: MIME type
            folder: Destination folder
            user_id: User ID for tracking
            
        Returns:
            Presigned URL data
        """
        # Validate file type by extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.allowed_extensions:
            raise FileValidationError(
                f"Invalid file extension. Allowed: {', '.join(self.allowed_extensions)}"
            )
        
        # Generate unique key
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid4())[:8]
        key = f"{folder}/{timestamp}_{unique_id}{ext}"
        
        # Generate presigned URL
        presigned_data = await self.storage.generate_presigned_upload_url(
            key=key,
            content_type=content_type,
            expires_in=3600,  # 1 hour
            max_size=self.max_file_size
        )
        
        return presigned_data
    
    async def validate_image_url(self, url: str) -> bool:
        """
        Validate if an image URL is accessible
        
        Args:
            url: Image URL to validate
            
        Returns:
            True if accessible, False otherwise
        """
        try:
            # Extract key from URL
            key = self.extract_key_from_url(url)
            if not key:
                return False
            
            # Check if file exists
            return await self.storage.file_exists(key)
        except Exception as e:
            logger.error(f"Error validating image URL {url}: {e}")
            return False
    
    async def get_file_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a file from its URL
        
        Args:
            url: File URL
            
        Returns:
            File information or None
        """
        key = self.extract_key_from_url(url)
        if not key:
            return None
        
        return await self.storage.get_file_info(key)


# Create service instance
media_service = MediaService()


# Convenience functions for direct import
def validate_image_file(file: UploadFile) -> bool:
    return media_service.validate_image_file(file)

async def upload_image(
    file: UploadFile,
    folder: str = "general",
    user_id: Optional[UUID] = None
) -> str:
    return await media_service.upload_image(file, folder, user_id)

async def delete_image(file_key: str, user_id: Optional[UUID] = None) -> bool:
    return await media_service.delete_image(file_key, user_id)

def extract_key_from_url(url: str) -> Optional[str]:
    return media_service.extract_key_from_url(url)

async def generate_presigned_upload_url(
    filename: str,
    content_type: str,
    folder: str = "general",
    user_id: Optional[UUID] = None
) -> Dict[str, Any]:
    return await media_service.generate_presigned_upload_url(
        filename, content_type, folder, user_id
    )

async def validate_image_url(url: str) -> bool:
    return await media_service.validate_image_url(url)
