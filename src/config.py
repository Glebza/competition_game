"""
Tournament Game Backend - Configuration Management
"""
import os
from typing import List, Optional, Union
from pathlib import Path

from pydantic import AnyHttpUrl, field_validator, PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    # Project metadata
    PROJECT_NAME: str = "Tournament Game"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Multiplayer voting tournament system"

    # Environment
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = True

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000

    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Allowed hosts for production
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]

    # Database Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "tournament_user"
    POSTGRES_PASSWORD: str = "tournament_password"
    POSTGRES_DB: str = "tournament_game"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    @field_validator("DATABASE_URL", mode='before')
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        if isinstance(v, str):
            return v
        data = info.data
        return f"postgresql+asyncpg://{data.get('POSTGRES_USER')}:{data.get('POSTGRES_PASSWORD')}@{data.get('POSTGRES_SERVER')}:{data.get('POSTGRES_PORT')}/{data.get('POSTGRES_DB')}"

    # Database pool settings
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False  # Set to True to log SQL queries

    # Storage Configuration (S3/MinIO)
    S3_ACCESS_KEY: str = "minio_access_key"
    S3_SECRET_KEY: str = "minio_secret_key"
    S3_BUCKET_NAME: str = "tournament-game-media"
    S3_ENDPOINT_URL: Optional[str] = "http://localhost:9000"  # MinIO for local dev
    S3_REGION: str = "us-east-1"
    S3_USE_SSL: bool = False

    # File upload settings
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]
    THUMBNAIL_SIZE: tuple = (400, 600)  # Width x Height

    # WebSocket Configuration
    WS_MESSAGE_QUEUE_SIZE: int = 100
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    WS_CONNECTION_TIMEOUT: int = 600  # 10 minutes

    # Game Session Configuration
    SESSION_CODE_LENGTH: int = 6
    SESSION_CODE_ALPHABET: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    MAX_PLAYERS_PER_SESSION: int = 100
    MIN_PLAYERS_PER_SESSION: int = 2

    # Tournament Configuration
    MAX_ITEMS_PER_COMPETITION: int = 128
    MIN_ITEMS_PER_COMPETITION: int = 4

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


    # Frontend URL (for CORS and links in emails)
    FRONTEND_URL: str = "http://localhost:3000"

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    STATIC_DIR: Path = BASE_DIR / "static"
    MEDIA_DIR: Path = BASE_DIR / "media"

    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @field_validator("ENVIRONMENT", mode='before')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        if v not in ["development", "staging", "production"]:
            raise ValueError("ENVIRONMENT must be one of: development, staging, production")
        return v

    @field_validator("DEBUG", mode='before')
    @classmethod
    def set_debug(cls, v: bool, info) -> bool:
        """Ensure DEBUG is False in production"""
        data = info.data
        if data.get("ENVIRONMENT") == "production":
            return False
        return v

    def get_db_url(self, async_driver: bool = True) -> str:
        """
        Get database URL with option for sync/async driver
        """
        driver = "asyncpg" if async_driver else "psycopg2"
        return f"postgresql+{driver}://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT == "production"

    @property
    def is_testing(self) -> bool:
        """Check if running in test mode"""
        return self.ENVIRONMENT == "testing"


# Create global settings instance
settings = Settings()

# Create directories if they don't exist
settings.STATIC_DIR.mkdir(exist_ok=True)
settings.MEDIA_DIR.mkdir(exist_ok=True)
