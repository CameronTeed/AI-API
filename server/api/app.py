"""
FastAPI application for AI Orchestrator
Provides REST endpoints for chat, admin operations, and health checks
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .routes import chat, admin, health

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle"""
    logger.info("🚀 Starting AI Orchestrator API")
    yield
    logger.info("🛑 Shutting down AI Orchestrator API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="AI Orchestrator API",
        description="REST API for AI-powered date ideas chat and admin management",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
    app.include_router(health.router, prefix="/api/health", tags=["health"])
    
    logger.info("✅ FastAPI application configured")
    
    return app


# Create the app instance
app = create_app()

