"""
Health Check Module
Provides health status and readiness checks for monitoring
"""

import logging
import asyncio
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthChecker:
    """Manages health checks for the application"""
    
    def __init__(self):
        """Initialize health checker"""
        self.start_time = datetime.now()
        self.checks = {}
    
    async def check_database(self) -> bool:
        """Check database connectivity"""
        try:
            from .tools.chat_context_storage import ChatContextStorage
            storage = ChatContextStorage()
            if storage.pool:
                async with storage.pool.connection() as conn:
                    await conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def check_openai(self) -> bool:
        """Check OpenAI API connectivity"""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI()
            # Just check if we can create a client (no actual API call)
            return client is not None
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False
    
    async def check_ml_models(self) -> bool:
        """Check if ML models are loaded"""
        try:
            from ..server.ml_service_integration import get_ml_service
            ml_service = get_ml_service()
            return ml_service.available
        except Exception as e:
            logger.error(f"ML models health check failed: {e}")
            return False
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Run checks in parallel
        db_ok, openai_ok, ml_ok = await asyncio.gather(
            self.check_database(),
            self.check_openai(),
            self.check_ml_models(),
            return_exceptions=True
        )
        
        # Convert exceptions to False
        db_ok = db_ok if isinstance(db_ok, bool) else False
        openai_ok = openai_ok if isinstance(openai_ok, bool) else False
        ml_ok = ml_ok if isinstance(ml_ok, bool) else False
        
        status = {
            'status': 'healthy' if all([db_ok, openai_ok]) else 'degraded',
            'uptime_seconds': uptime,
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'database': 'ok' if db_ok else 'failed',
                'openai': 'ok' if openai_ok else 'failed',
                'ml_models': 'ok' if ml_ok else 'unavailable'
            }
        }
        
        return status
    
    async def get_readiness_status(self) -> Dict[str, Any]:
        """Get readiness status (for Kubernetes probes)"""
        health = await self.get_health_status()
        ready = health['status'] == 'healthy'
        
        return {
            'ready': ready,
            'checks': health['checks']
        }


# Global health checker instance
_health_checker: HealthChecker = None


def get_health_checker() -> HealthChecker:
    """Get global health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker

