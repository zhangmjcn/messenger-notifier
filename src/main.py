"""
FastAPI Notification Service
Main application entry point with loguru logging and multi-layer configuration.
"""
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import settings
from src.routers import notifier


def setup_logging():
    """Configure loguru logging with appropriate format and level."""
    # Remove default logger
    logger.remove()
    
    # Add console logger with custom format
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True
    )
    
    # Add file logger for persistent logs in data directory
    import os
    log_dir = "./data" if os.path.exists("./data") else "./logs"
    os.makedirs(log_dir, exist_ok=True)
    logger.add(
        f"{log_dir}/notify-service.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    logger.info(f"Logging configured - Level: {settings.log_level}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup/shutdown events."""
    # Startup
    logger.info("=== FastAPI Notification Service Starting ===")
    logger.info(f"Service configuration loaded - Port: {settings.api_port}")
    
    # Log adapter status
    if settings.telegram_bot_token:
        logger.info("Telegram adapter: CONFIGURED")
    else:
        logger.warning("Telegram adapter: NOT CONFIGURED")
    
    if settings.feishu_app_id and settings.feishu_app_secret:
        logger.info("Feishu application credentials: CONFIGURED")
        if settings.feishu_default_user_id:
            logger.info("Feishu default user ID: CONFIGURED")
        else:
            logger.warning("Feishu default user ID: NOT CONFIGURED - require receive_id in API requests")
    else:
        logger.error("Feishu application credentials: NOT CONFIGURED")
        logger.error("⚠️  Feishu API will return 503 errors. Please configure FEISHU_APP_ID and FEISHU_APP_SECRET")
    
    logger.success("=== Service startup completed ===")
    
    yield
    
    # Shutdown
    logger.info("=== Service shutting down ===")


# Configure logging before creating app
setup_logging()

# Create FastAPI application
app = FastAPI(
    title="Notification Service API",
    description="FastAPI service for sending notifications to Telegram and Feishu platforms",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(notifier.router)


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Notification Service API",
        "version": "1.0.0",
        "status": "running",
        "port": settings.api_port,
        "endpoints": {
            "telegram": "/notifier/notify_telegram",
            "feishu": "/notifier/notify_feishu",
            "health": "/notifier/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def global_health():
    """Global health check endpoint."""
    return {
        "status": "healthy",
        "service": "notification-service",
        "version": "1.0.0"
    }


def main():
    """Main entry point for the notification service."""
    import uvicorn
    
    logger.info(f"Starting Notification Service on port {settings.api_port}")
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=False,  # Disable reload in production
        log_config=None  # Use loguru instead of uvicorn logging
    )


if __name__ == "__main__":
    main()