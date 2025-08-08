"""
Tournament Game Backend - Media API Endpoints
"""
import os
from typing import List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse

from src.api import deps
from src.api.v1.schemas.media import (
    MediaUploadResponse,
    MediaDeleteResponse,
    MediaBulkUploadResponse
)
from src.config import settings
from src.modules.media import service as media_service
from src.modules.media.exceptions import (
    FileUploadError,
    FileValidationError,
    FileNotFoundError,
    FileSizeLimitError
)

router = APIRouter()


@router.post("/upload", response_model=MediaUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    folder: str = "general",
    current_user_id: UUID = Depends(deps.get_current_user_id_optional)
) -> MediaUploadResponse:
    """
    Upload a single image file
    
    - **file**: Image file (JPG, PNG, WebP)
    - **folder**: Destination folder in storage (default: "general")
    """
    try:
        # Validate file
        if not media_service.validate_image_file(file):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}"
            )
        
        # Check file size
        if file.size and file.size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB"
            )
        
        # Upload file
        file_url = await media_service.upload_image(
            file=file,
            folder=folder,
            user_id=current_user_id
        )
        
        return MediaUploadResponse(
            url=file_url,
            filename=file.filename,
            size=file.size or 0,
            content_type=file.content_type
        )
        
    except FileUploadError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )
    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FileSizeLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e)
        )


@router.post("/upload-multiple", response_model=MediaBulkUploadResponse)
async def upload_multiple_images(
    files: List[UploadFile] = File(...),
    folder: str = "general",
    current_user_id: UUID = Depends(deps.get_current_user_id_optional)
) -> MediaBulkUploadResponse:
    """
    Upload multiple image files at once
    
    - **files**: List of image files (JPG, PNG, WebP)
    - **folder**: Destination folder in storage (default: "general")
    - **Maximum files**: 50 per request
    """
    # Validate file count
    if len(files) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 files can be uploaded at once"
        )
    
    if len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file must be provided"
        )
    
    uploaded_files = []
    failed_files = []
    
    for file in files:
        try:
            # Validate file
            if not media_service.validate_image_file(file):
                failed_files.append({
                    "filename": file.filename,
                    "error": f"Invalid file type"
                })
                continue
            
            # Check file size
            if file.size and file.size > settings.MAX_UPLOAD_SIZE:
                failed_files.append({
                    "filename": file.filename,
                    "error": f"File size exceeds {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB"
                })
                continue
            
            # Upload file
            file_url = await media_service.upload_image(
                file=file,
                folder=folder,
                user_id=current_user_id
            )
            
            uploaded_files.append({
                "url": file_url,
                "filename": file.filename,
                "size": file.size or 0,
                "content_type": file.content_type
            })
            
        except Exception as e:
            failed_files.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return MediaBulkUploadResponse(
        uploaded=uploaded_files,
        failed=failed_files,
        total_uploaded=len(uploaded_files),
        total_failed=len(failed_files)
    )


@router.delete("/delete", response_model=MediaDeleteResponse)
async def delete_image(
    file_url: str,
    current_user_id: UUID = Depends(deps.get_current_user_id_optional)
) -> MediaDeleteResponse:
    """
    Delete an uploaded image by URL
    
    - **file_url**: Full URL of the file to delete
    """
    try:
        # Extract key from URL
        file_key = media_service.extract_key_from_url(file_url)
        if not file_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file URL"
            )
        
        # Delete file
        success = await media_service.delete_image(file_key, user_id=current_user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or already deleted"
            )
        
        return MediaDeleteResponse(
            success=True,
            message="File deleted successfully"
        )
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


@router.post("/generate-presigned-url")
async def generate_presigned_upload_url(
    filename: str,
    content_type: str = "image/jpeg",
    folder: str = "general",
    current_user_id: UUID = Depends(deps.get_current_user_id_optional)
) -> dict:
    """
    Generate a presigned URL for direct browser upload to S3
    
    - **filename**: Original filename
    - **content_type**: MIME type of the file
    - **folder**: Destination folder in storage
    """
    # Validate content type
    valid_types = ["image/jpeg", "image/png", "image/webp"]
    if content_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type. Allowed types: {', '.join(valid_types)}"
        )
    
    # Validate filename extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Allowed: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}"
        )
    
    try:
        # Generate presigned URL
        presigned_data = await media_service.generate_presigned_upload_url(
            filename=filename,
            content_type=content_type,
            folder=folder,
            user_id=current_user_id
        )
        
        return presigned_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {str(e)}"
        )


@router.get("/validate-image")
async def validate_image_url(url: str) -> dict:
    """
    Validate if an image URL is accessible and valid
    
    - **url**: Image URL to validate
    """
    try:
        is_valid = await media_service.validate_image_url(url)
        
        return {
            "valid": is_valid,
            "url": url
        }
    except Exception as e:
        return {
            "valid": False,
            "url": url,
            "error": str(e)
        }
