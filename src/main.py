"""
Tournament Game Backend - Main Application Entry Point
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.api.v1.router import api_router
from src.config import settings
from src.core.database import engine
from src.core.exceptions import TournamentGameException
from src.infrastructure.ws.connection_manager import connection_manager
from src.modules.competition.models import Base as CompetitionBase
from src.modules.session.models import Base as SessionBase
from src.modules.user.models import Base as UserBase

# Configure logging
import os
from pathlib import Path

# Create logs directory if it doesn't exist
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Configure logging with both file and console handlers
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(logs_dir / "app.log"),
        logging.StreamHandler()  # Console output
    ]
)
logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests"""
    
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Response: {response.status_code}")
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Manage application lifecycle - startup and shutdown events
    """
    # Startup
    logger.info("Starting up Tournament Game Backend...")
    
    # Initialize database tables (for development only)
    if settings.ENVIRONMENT == "development":
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(CompetitionBase.metadata.create_all)
            await conn.run_sync(SessionBase.metadata.create_all)
            await conn.run_sync(UserBase.metadata.create_all)
            logger.info("Database tables created successfully")
    
    # Initialize WebSocket connection manager
    await connection_manager.initialize()
    logger.info("WebSocket connection manager initialized")
    
    logger.info("Startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Tournament Game Backend...")
    
    # Close database connections
    await engine.dispose()
    logger.info("Database connections closed")
    
    # Clean up WebSocket connections
    await connection_manager.cleanup()
    logger.info("WebSocket connections cleaned up")
    
    logger.info("Shutdown complete")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Backend API for Tournament Game - A multiplayer voting tournament system",
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.ENVIRONMENT != "production" else None,
        docs_url=f"{settings.API_V1_STR}/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url=f"{settings.API_V1_STR}/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan
    )
    
    # Add middlewares
    app.add_middleware(LoggingMiddleware)
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Trusted host middleware for security
    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )
    
    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint - API health check"""
        return {
            "message": "Tournament Game API",
            "version": settings.VERSION,
            "status": "running",
            "environment": settings.ENVIRONMENT
        }
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """
        Health check endpoint for monitoring
        """
        health_status = {
            "status": "healthy",
            "database": "unknown"
        }
        
        # Check database
        try:
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
            health_status["database"] = "healthy"
        except Exception as e:
            health_status["database"] = "unhealthy"
            health_status["status"] = "degraded"
            logger.error(f"Database health check failed: {e}")
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(content=health_status, status_code=status_code)
    
    # Global exception handler
    @app.exception_handler(TournamentGameException)
    async def tournament_exception_handler(request: Request, exc: TournamentGameException):
        """Handle custom application exceptions"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "code": exc.code
            }
        )
    
    # Generic exception handler for production
    if settings.ENVIRONMENT == "production":
        @app.exception_handler(Exception)
        async def generic_exception_handler(request: Request, exc: Exception):
            """Handle unexpected exceptions in production"""
            logger.error(f"Unexpected error: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "code": "INTERNAL_ERROR"
                }
            )
    
    return app


# Create the application instance
app = create_application()


if __name__ == "__main__":
    # Run the application with Uvicorn when executed directly
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level="info",
        access_log=True
    )
