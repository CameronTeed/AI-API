"""
ML Service Integration Wrapper
Provides unified interface to ML service for vibe prediction and date planning
"""

import logging
from typing import List, Dict, Any, Optional
from functools import lru_cache
import asyncio

logger = logging.getLogger(__name__)


class MLServiceWrapper:
    """Wrapper around ML service with caching and error handling"""
    
    def __init__(self):
        """Initialize ML service wrapper"""
        try:
            from ..ml_service_integration import get_ml_service
            self.ml_service = get_ml_service()
            self.available = self.ml_service.available
            logger.info("✅ ML Service initialized")
        except Exception as e:
            logger.warning(f"⚠️  ML Service not available: {e}")
            self.ml_service = None
            self.available = False
        
        # Cache for vibe predictions
        self._vibe_cache = {}
        self._cache_size = 1000
    
    def predict_vibe(self, text: str) -> str:
        """Predict vibe from text with caching"""
        if not self.available:
            return "casual"
        
        # Check cache
        if text in self._vibe_cache:
            return self._vibe_cache[text]
        
        try:
            vibe = self.ml_service.predict_vibe(text)
            
            # Cache result (with size limit)
            if len(self._vibe_cache) < self._cache_size:
                self._vibe_cache[text] = vibe
            
            return vibe
        except Exception as e:
            logger.warning(f"Error predicting vibe: {e}")
            return "casual"
    
    def predict_vibes_batch(self, texts: List[str]) -> List[str]:
        """Predict vibes for multiple texts"""
        if not self.available:
            return ["casual"] * len(texts)
        
        try:
            return self.ml_service.predict_vibes_batch(texts)
        except Exception as e:
            logger.warning(f"Error predicting vibes: {e}")
            return ["casual"] * len(texts)
    
    def plan_date(self, preferences: Dict[str, Any], algorithm: str = "heuristic") -> Optional[Dict[str, Any]]:
        """Plan a date based on preferences"""
        if not self.available:
            return None
        
        try:
            if algorithm == "genetic":
                return self.ml_service.plan_date_genetic(preferences)
            else:
                return self.ml_service.plan_date_heuristic(preferences)
        except Exception as e:
            logger.warning(f"Error planning date: {e}")
            return None
    
    def clear_cache(self):
        """Clear vibe prediction cache"""
        self._vibe_cache.clear()
        logger.debug("Vibe cache cleared")


# Global instance
_ml_wrapper = None


def get_ml_wrapper() -> MLServiceWrapper:
    """Get or create ML service wrapper instance"""
    global _ml_wrapper
    if _ml_wrapper is None:
        _ml_wrapper = MLServiceWrapper()
    return _ml_wrapper

