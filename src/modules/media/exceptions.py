"""
Tournament Game Backend - Media Exceptions
Custom exceptions for media-related errors
"""
from src.core.exceptions import (
    TournamentGameException,
    ValidationError,
    NotFoundError,
    PayloadTooLargeError,
    BadRequestError
)


class MediaError(TournamentGameException):
    """Base exception for all media-related errors"""
    pass


class FileUploadError(MediaError):
    """Raised when file upload fails"""
    def __init__(self, detail: str = "File upload failed"):
        super().__init__(
            detail=detail,
            status_code=500,
            code="FILE_UPLOAD_ERROR"
        )


class FileValidationError(ValidationError):
    """Raised when file validation fails"""
    def __init__(self, detail: str = "Invalid file"):
        super().__init__(
            detail=detail,
            code="FILE_VALIDATION_ERROR"
        )


class FileNotFoundError(NotFoundError):
    """Raised when a file is not found"""
    def __init__(self, detail: str = "File not found"):
        super().__init__(
            detail=detail,
            code="FILE_NOT_FOUND"
        )


class FileSizeLimitError(PayloadTooLargeError):
    """Raised when file size exceeds limit"""
    def __init__(self, detail: str = "File size exceeds maximum allowed size"):
        super().__init__(
            detail=detail,
            code="FILE_SIZE_LIMIT"
        )


class ImageProcessingError(MediaError):
    """Raised when image processing fails"""
    def __init__(self, detail: str = "Image processing failed"):
        super().__init__(
            detail=detail,
            status_code=422,
            code="IMAGE_PROCESSING_ERROR"
        )


class UnsupportedFileTypeError(ValidationError):
    """Raised when file type is not supported"""
    def __init__(self, detail: str = "Unsupported file type"):
        super().__init__(
            detail=detail,
            code="UNSUPPORTED_FILE_TYPE"
        )


class StorageError(MediaError):
    """Raised when storage operation fails"""
    def __init__(self, detail: str = "Storage operation failed"):
        super().__init__(
            detail=detail,
            status_code=503,
            code="STORAGE_ERROR"
        )


class InvalidImageDimensionsError(ValidationError):
    """Raised when image dimensions are invalid"""
    def __init__(self, detail: str = "Invalid image dimensions"):
        super().__init__(
            detail=detail,
            code="INVALID_IMAGE_DIMENSIONS"
        )
