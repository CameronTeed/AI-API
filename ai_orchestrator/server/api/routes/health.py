"""
Health check endpoints
"""

import logging
from fastapi import APIRouter
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def health_status():
    """Get overall health status of the service"""
    try:
        from ...chat_handler import EnhancedChatHandler
        
        handler = EnhancedChatHandler()
        
        health_details = {
            "llm_engine": "healthy" if handler.llm_engine else "unhealthy",
            "vector_store": "healthy" if handler.vector_store else "unhealthy",
            "web_client": "healthy" if handler.web_client else "unhealthy",
            "agent_tools": "healthy" if handler.agent_tools else "unhealthy",
            "chat_storage": "healthy" if handler.chat_storage else "unhealthy",
        }
        
        overall_status = "healthy" if all(v == "healthy" for v in health_details.values()) else "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": health_details
        }
    
    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/ready")
async def readiness_check():
    """Check if service is ready to accept requests"""
    try:
        from ...chat_handler import EnhancedChatHandler
        
        handler = EnhancedChatHandler()
        
        # Check critical components
        if not handler.llm_engine or not handler.chat_storage:
            return {
                "ready": False,
                "reason": "Critical components not initialized"
            }
        
        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Readiness check error: {e}", exc_info=True)
        return {
            "ready": False,
            "reason": str(e)
        }

