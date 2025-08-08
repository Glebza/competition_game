"""
Tournament Game Backend - Storage Configuration
S3/MinIO storage client for media files
"""
import logging
from typing import Optional, Dict, Any, BinaryIO
from datetime import datetime, timedelta
import mimetypes
from pathlib import Path

import aioboto3
from botocore.exceptions import ClientError, NoCredentialsError

from src.config import settings
from src.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class StorageClient:
    """
    Async S3/MinIO storage client for media file operations
    """
    
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.session = aioboto3.Session(
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION
        )
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.use_ssl = settings.S3_USE_SSL
    
    async def _get_client(self):
        """Get S3 client"""
        return self.session.client(
            's3',
            endpoint_url=self.endpoint_url,
            use_ssl=self.use_ssl
        )
    
    async def ensure_bucket_exists(self) -> bool:
        """
        Ensure the bucket exists, create if not.
        
        Returns:
            True if bucket exists or was created successfully
        """
        async with await self._get_client() as client:
            try:
                await client.head_bucket(Bucket=self.bucket_name)
                logger.info(f"Bucket {self.bucket_name} exists")
                return True
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    # Bucket doesn't exist, create it
                    try:
                        await client.create_bucket(Bucket=self.bucket_name)
                        logger.info(f"Created bucket {self.bucket_name}")
                        
                        # Set bucket policy for public read (if needed)
                        if settings.is_development:
                            await self._set_public_read_policy()
                        
                        return True
                    except ClientError as create_error:
                        logger.error(f"Failed to create bucket: {create_error}")
                        return False
                else:
                    logger.error(f"Error checking bucket: {e}")
                    return False
    
    async def _set_public_read_policy(self):
        """Set public read policy for development"""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicRead",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": f"arn:aws:s3:::{self.bucket_name}/*"
                }
            ]
        }
        
        async with await self._get_client() as client:
            import json
            await client.put_bucket_policy(
                Bucket=self.bucket_name,
                Policy=json.dumps(policy)
            )
    
    async def upload_file(
        self,
        file_content: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload a file to S3/MinIO.
        
        Args:
            file_content: File content to upload
            key: S3 key (path) for the file
            content_type: MIME type of the file
            metadata: Additional metadata
        
        Returns:
            Public URL of the uploaded file
        
        Raises:
            ExternalServiceError: If upload fails
        """
        try:
            # Ensure bucket exists
            await self.ensure_bucket_exists()
            
            # Prepare upload arguments
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            else:
                # Try to guess content type
                content_type = mimetypes.guess_type(key)[0]
                if content_type:
                    extra_args['ContentType'] = content_type
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Upload file
            async with await self._get_client() as client:
                await client.upload_fileobj(
                    file_content,
                    self.bucket_name,
                    key,
                    ExtraArgs=extra_args
                )
            
            logger.info(f"Successfully uploaded file to {key}")
            
            # Return public URL
            return self.get_public_url(key)
            
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Failed to upload file: {e}")
            raise ExternalServiceError(
                service_name="S3",
                detail=f"Failed to upload file: {str(e)}"
            )
    
    async def delete_file(self, key: str) -> bool:
        """
        Delete a file from S3/MinIO.
        
        Args:
            key: S3 key of the file to delete
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            async with await self._get_client() as client:
                await client.delete_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
            logger.info(f"Successfully deleted file {key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file: {e}")
            return False
    
    async def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in S3/MinIO.
        
        Args:
            key: S3 key to check
        
        Returns:
            True if file exists, False otherwise
        """
        try:
            async with await self._get_client() as client:
                await client.head_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
            return True
        except ClientError:
            return False
    
    async def get_file_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get file information from S3/MinIO.
        
        Args:
            key: S3 key of the file
        
        Returns:
            File information dict or None if not found
        """
        try:
            async with await self._get_client() as client:
                response = await client.head_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
            
            return {
                'size': response['ContentLength'],
                'content_type': response.get('ContentType'),
                'last_modified': response['LastModified'],
                'metadata': response.get('Metadata', {}),
                'etag': response['ETag'].strip('"')
            }
        except ClientError:
            return None
    
    async def generate_presigned_upload_url(
        self,
        key: str,
        content_type: Optional[str] = None,
        expires_in: int = 3600,
        max_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL for direct upload.
        
        Args:
            key: S3 key for the file
            content_type: Expected content type
            expires_in: URL expiration time in seconds
            max_size: Maximum file size allowed
        
        Returns:
            Dict with upload_url and other fields
        """
        try:
            conditions = []
            fields = {}
            
            if content_type:
                conditions.append(["eq", "$Content-Type", content_type])
                fields['Content-Type'] = content_type
            
            if max_size:
                conditions.append(["content-length-range", 0, max_size])
            
            async with await self._get_client() as client:
                response = await client.generate_presigned_post(
                    Bucket=self.bucket_name,
                    Key=key,
                    Fields=fields,
                    Conditions=conditions,
                    ExpiresIn=expires_in
                )
            
            return {
                'upload_url': response['url'],
                'fields': response['fields'],
                'file_url': self.get_public_url(key),
                'expires_at': datetime.utcnow() + timedelta(seconds=expires_in),
                'max_size': max_size or settings.MAX_UPLOAD_SIZE
            }
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise ExternalServiceError(
                service_name="S3",
                detail=f"Failed to generate upload URL: {str(e)}"
            )
    
    async def list_files(
        self,
        prefix: Optional[str] = None,
        max_keys: int = 1000
    ) -> list[Dict[str, Any]]:
        """
        List files in S3/MinIO.
        
        Args:
            prefix: Filter files by prefix
            max_keys: Maximum number of files to return
        
        Returns:
            List of file information dicts
        """
        try:
            async with await self._get_client() as client:
                params = {
                    'Bucket': self.bucket_name,
                    'MaxKeys': max_keys
                }
                if prefix:
                    params['Prefix'] = prefix
                
                response = await client.list_objects_v2(**params)
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag'].strip('"'),
                    'url': self.get_public_url(obj['Key'])
                })
            
            return files
            
        except ClientError as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def get_public_url(self, key: str) -> str:
        """
        Get public URL for a file.
        
        Args:
            key: S3 key of the file
        
        Returns:
            Public URL
        """
        if self.endpoint_url:
            # MinIO or custom S3 endpoint
            base_url = self.endpoint_url.rstrip('/')
            return f"{base_url}/{self.bucket_name}/{key}"
        else:
            # AWS S3
            return f"https://{self.bucket_name}.s3.{settings.S3_REGION}.amazonaws.com/{key}"
    
    def extract_key_from_url(self, url: str) -> Optional[str]:
        """
        Extract S3 key from a public URL.
        
        Args:
            url: Public URL of the file
        
        Returns:
            S3 key or None if invalid URL
        """
        # Remove protocol
        if url.startswith('http://') or url.startswith('https://'):
            url = url.split('://', 1)[1]
        
        # Extract key based on URL pattern
        if self.endpoint_url:
            # MinIO pattern: endpoint/bucket/key
            prefix = self.endpoint_url.replace('http://', '').replace('https://', '')
            pattern = f"{prefix}/{self.bucket_name}/"
            if pattern in url:
                return url.split(pattern, 1)[1]
        else:
            # AWS S3 pattern
            pattern = f"{self.bucket_name}.s3.{settings.S3_REGION}.amazonaws.com/"
            if pattern in url:
                return url.split(pattern, 1)[1]
        
        return None


# Create global storage client instance
storage_client = StorageClient()
