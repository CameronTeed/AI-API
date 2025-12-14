"""
Rate limiting middleware for FastAPI
Applies per-account rate limiting based on account tier
"""

import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from ..rate_limiting import get_rate_limiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to apply per-account rate limiting
    Extracts account ID and tier from request and checks limits
    """
    
    # Endpoints that should skip rate limiting
    SKIP_RATE_LIMIT_PATHS = {
        "/api/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/swagger-ui",
    }
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        
        # Skip rate limiting for certain paths
        if any(request.url.path.startswith(path) for path in self.SKIP_RATE_LIMIT_PATHS):
            return await call_next(request)
        
        # Extract account ID and tier from request
        # Priority: header > query param > default
        account_id = (
            request.headers.get("X-Account-ID") or
            request.query_params.get("account_id") or
            "anonymous"
        )
        
        account_tier = (
            request.headers.get("X-Account-Tier") or
            request.query_params.get("account_tier") or
            "free"
        )
        
        # Check rate limit
        rate_limiter = get_rate_limiter()
        allowed, reason = rate_limiter.check_rate_limit(account_id, account_tier)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for account {account_id}: {reason}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": reason,
                    "account_id": account_id,
                    "tier": account_tier,
                }
            )
        
        # Consume request
        rate_limiter.consume_request(account_id)
        
        # Increment concurrent counter
        rate_limiter.increment_concurrent(account_id)
        
        try:
            # Process request
            response = await call_next(request)
        finally:
            # Decrement concurrent counter
            rate_limiter.decrement_concurrent(account_id)
        
        # Add rate limit headers to response
        stats = rate_limiter.get_account_stats(account_id)
        response.headers["X-RateLimit-Minute"] = str(stats.get("minute_requests", 0))
        response.headers["X-RateLimit-Hour"] = str(stats.get("hour_requests", 0))
        response.headers["X-RateLimit-Day"] = str(stats.get("day_requests", 0))
        response.headers["X-RateLimit-Concurrent"] = str(stats.get("concurrent_requests", 0))
        
        return response

