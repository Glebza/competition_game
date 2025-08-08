"""
Tournament Game Backend - Image Processor
Image optimization and thumbnail generation
"""
import logging
import io
from typing import Optional, Tuple, BinaryIO
from PIL import Image, ImageOps

from src.config import settings
from src.modules.media.exceptions import ImageProcessingError

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Handles image processing operations like resizing and optimization"""
    
    def __init__(self):
        self.thumbnail_size = settings.THUMBNAIL_SIZE
        self.max_size = (2048, 2048)  # Maximum dimensions for uploaded images
        self.quality = 85  # JPEG quality
    
    async def process_image(
        self,
        image_data: bytes,
        optimize: bool = True,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        quality: Optional[int] = None
    ) -> bytes:
        """
        Process an image - resize and optimize
        
        Args:
            image_data: Raw image bytes
            optimize: Whether to optimize the image
            max_width: Maximum width (optional)
            max_height: Maximum height (optional)
            quality: JPEG quality (1-100)
            
        Returns:
            Processed image bytes
            
        Raises:
            ImageProcessingError: If processing fails
        """
        try:
            # Open image
            with Image.open(io.BytesIO(image_data)) as img:
                # Convert RGBA to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    # Create a white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Fix orientation based on EXIF data
                img = ImageOps.exif_transpose(img)
                
                # Resize if needed
                if max_width or max_height:
                    img = self._resize_image(img, max_width, max_height)
                else:
                    # Apply default max size
                    img = self._resize_image(img, self.max_size[0], self.max_size[1])
                
                # Save to bytes
                output = io.BytesIO()
                save_kwargs = {
                    'format': 'JPEG',
                    'quality': quality or self.quality,
                    'optimize': optimize
                }
                
                img.save(output, **save_kwargs)
                return output.getvalue()
                
        except Exception as e:
            logger.error(f"Failed to process image: {e}")
            raise ImageProcessingError(f"Failed to process image: {str(e)}")
    
    async def generate_thumbnail(
        self,
        image_data: bytes,
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> bytes:
        """
        Generate a thumbnail from an image
        
        Args:
            image_data: Raw image bytes
            width: Thumbnail width (default from settings)
            height: Thumbnail height (default from settings)
            
        Returns:
            Thumbnail image bytes
        """
        try:
            # Use provided dimensions or defaults
            thumb_width = width or self.thumbnail_size[0]
            thumb_height = height or self.thumbnail_size[1]
            
            with Image.open(io.BytesIO(image_data)) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Fix orientation
                img = ImageOps.exif_transpose(img)
                
                # Create thumbnail using LANCZOS resampling
                img.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)
                
                # Center crop to exact dimensions
                if img.size != (thumb_width, thumb_height):
                    img = self._center_crop(img, thumb_width, thumb_height)
                
                # Save thumbnail
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=90, optimize=True)
                return output.getvalue()
                
        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            raise ImageProcessingError(f"Failed to generate thumbnail: {str(e)}")
    
    def _resize_image(
        self,
        img: Image.Image,
        max_width: int,
        max_height: int
    ) -> Image.Image:
        """
        Resize image to fit within max dimensions while maintaining aspect ratio
        
        Args:
            img: PIL Image object
            max_width: Maximum width
            max_height: Maximum height
            
        Returns:
            Resized image
        """
        # Calculate the scaling factor
        width_ratio = max_width / img.width
        height_ratio = max_height / img.height
        scale_factor = min(width_ratio, height_ratio)
        
        # Only resize if image is larger than max dimensions
        if scale_factor < 1:
            new_width = int(img.width * scale_factor)
            new_height = int(img.height * scale_factor)
            return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return img
    
    def _center_crop(
        self,
        img: Image.Image,
        width: int,
        height: int
    ) -> Image.Image:
        """
        Center crop an image to exact dimensions
        
        Args:
            img: PIL Image object
            width: Target width
            height: Target height
            
        Returns:
            Cropped image
        """
        left = (img.width - width) // 2
        top = (img.height - height) // 2
        right = left + width
        bottom = top + height
        
        return img.crop((left, top, right, bottom))
    
    async def get_image_info(self, image_data: bytes) -> dict:
        """
        Get information about an image
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Dictionary with image information
        """
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'size_bytes': len(image_data)
                }
        except Exception as e:
            logger.error(f"Failed to get image info: {e}")
            raise ImageProcessingError(f"Failed to get image info: {str(e)}")
    
    def validate_image_dimensions(
        self,
        width: int,
        height: int,
        min_width: int = 100,
        min_height: int = 100
    ) -> bool:
        """
        Validate if image dimensions are acceptable
        
        Args:
            width: Image width
            height: Image height
            min_width: Minimum acceptable width
            min_height: Minimum acceptable height
            
        Returns:
            True if dimensions are valid
        """
        return width >= min_width and height >= min_height


# Create processor instance
image_processor = ImageProcessor()
