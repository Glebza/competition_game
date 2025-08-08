"""
Tournament Game Backend - Database Configuration
PostgreSQL database setup with SQLAlchemy async support
"""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from src.config import settings

logger = logging.getLogger(__name__)

# Create async engine
if settings.is_development:
    # Use NullPool for development to avoid connection issues
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        poolclass=NullPool,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
    )
else:
    # Use connection pooling for production
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
    )

# Create async session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create declarative base
Base = declarative_base()

# Metadata for migrations
metadata = Base.metadata


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    This is used by FastAPI's dependency injection.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.
    Only used for development - production uses Liquibase migrations.
    """
    if not settings.is_development:
        logger.warning("Database initialization should only be run in development!")
        return
    
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from src.modules.user.models import User
        from src.modules.competition.models import Competition, CompetitionItem
        from src.modules.session.models import GameSession, SessionPlayer, Vote, SessionRound
        
        # Create all tables
        await conn.run_sync(metadata.create_all)
        logger.info("Database tables created successfully")


async def check_database_connection() -> bool:
    """
    Check if database is accessible.
    Used for health checks.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def close_database() -> None:
    """
    Close database connections.
    Called during application shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")
