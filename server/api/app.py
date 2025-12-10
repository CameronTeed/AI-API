"""
FastAPI application for AI Orchestrator
Provides REST endpoints for chat, admin operations, and health checks
"""

import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .routes import chat, admin, health
from . import ml_endpoints

logger = logging.getLogger(__name__)

# Initialize rate limiter: 100 requests per minute per IP
limiter = Limiter(key_func=get_remote_address)


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

    # Add rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    app.include_router(ml_endpoints.router, tags=["ml-service"])

    logger.info("✅ FastAPI application configured with rate limiting (100 req/min)")

    return app


async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors"""
    logger.warning(f"Rate limit exceeded for {get_remote_address(request)}")
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded. Max 100 requests per minute."}
    )


# Create the app instance
app = create_app()

