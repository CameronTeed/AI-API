"""
Base Tool Class
Provides common interface for all tools
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    def __init__(self, name: str, description: str):
        """Initialize base tool"""
        self.name = name
        self.description = description
        self.last_used = None
        self.call_count = 0
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes default
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool - must be implemented by subclasses"""
        pass
    
    async def call(self, **kwargs) -> Dict[str, Any]:
        """Call the tool with caching and error handling"""
        try:
            self.call_count += 1
            self.last_used = datetime.now()
            
            # Check cache
            cache_key = self._make_cache_key(kwargs)
            if cache_key in self._cache:
                cached_result, timestamp = self._cache[cache_key]
                if datetime.now() - timestamp < timedelta(seconds=self._cache_ttl):
                    logger.debug(f"Cache hit for {self.name}")
                    return cached_result
            
            # Execute tool
            result = await self.execute(**kwargs)
            
            # Cache result
            self._cache[cache_key] = (result, datetime.now())
            
            return result
        except Exception as e:
            logger.error(f"Error executing {self.name}: {e}")
            return {'error': str(e), 'success': False}
    
    def _make_cache_key(self, kwargs: Dict[str, Any]) -> str:
        """Create cache key from kwargs"""
        items = sorted(kwargs.items())
        return str(items)
    
    def clear_cache(self):
        """Clear tool cache"""
        self._cache.clear()
        logger.debug(f"Cache cleared for {self.name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tool statistics"""
        return {
            'name': self.name,
            'call_count': self.call_count,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'cache_size': len(self._cache)
        }


class SearchTool(BaseTool):
    """Base class for search tools"""
    
    def __init__(self, name: str, description: str):
        """Initialize search tool"""
        super().__init__(name, description)
        self._cache_ttl = 600  # 10 minutes for search results
    
    async def search(self, query: str, limit: int = 10, **kwargs) -> Dict[str, Any]:
        """Search interface"""
        return await self.call(query=query, limit=limit, **kwargs)


class LocationTool(BaseTool):
    """Base class for location-based tools"""
    
    def __init__(self, name: str, description: str):
        """Initialize location tool"""
        super().__init__(name, description)
    
    async def find_nearby(
        self,
        latitude: float,
        longitude: float,
        radius: int = 5000,
        **kwargs
    ) -> Dict[str, Any]:
        """Find nearby locations"""
        return await self.call(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            **kwargs
        )

