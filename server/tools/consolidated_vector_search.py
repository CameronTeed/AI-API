"""
Consolidated Vector Search Tool
Replaces both vector_store.py and postgresql_vector_store.py
"""

import logging
from typing import List, Dict, Any, Optional
from .base_tool import SearchTool

logger = logging.getLogger(__name__)


class VectorSearchTool(SearchTool):
    """Unified vector search tool"""
    
    def __init__(self, db_client=None):
        """Initialize vector search tool"""
        super().__init__(
            name="vector_search",
            description="Semantic search using vector embeddings"
        )
        self.db_client = db_client
        self._cache_ttl = 600  # 10 minutes
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute vector search"""
        try:
            query = kwargs.get('query', '')
            limit = kwargs.get('limit', 10)
            filters = kwargs.get('filters', {})
            
            if not query:
                return {'results': [], 'count': 0, 'success': False}
            
            if not self.db_client:
                logger.warning("Database client not available")
                return {'results': [], 'count': 0, 'success': False}
            
            # Use database client for vector search
            results = await self.db_client.vector_search(
                query=query,
                limit=limit,
                filters=filters
            )
            
            return {
                'results': results,
                'count': len(results),
                'success': True,
                'query': query
            }
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return {'results': [], 'count': 0, 'success': False, 'error': str(e)}
    
    async def search_by_vibe(
        self,
        vibes: List[str],
        limit: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """Search by vibe tags"""
        try:
            if not self.db_client:
                return {'results': [], 'count': 0, 'success': False}
            
            results = await self.db_client.search_by_metadata(
                metadata_key='vibe',
                metadata_values=vibes,
                limit=limit
            )
            
            return {
                'results': results,
                'count': len(results),
                'success': True,
                'vibes': vibes
            }
        except Exception as e:
            logger.error(f"Vibe search error: {e}")
            return {'results': [], 'count': 0, 'success': False, 'error': str(e)}
    
    async def search_by_location(
        self,
        latitude: float,
        longitude: float,
        radius_km: int = 5,
        limit: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """Search by location"""
        try:
            if not self.db_client:
                return {'results': [], 'count': 0, 'success': False}
            
            results = await self.db_client.search_by_location(
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                limit=limit
            )
            
            return {
                'results': results,
                'count': len(results),
                'success': True,
                'location': {'lat': latitude, 'lon': longitude, 'radius_km': radius_km}
            }
        except Exception as e:
            logger.error(f"Location search error: {e}")
            return {'results': [], 'count': 0, 'success': False, 'error': str(e)}


# Global instance
_vector_search_tool = None


def get_vector_search_tool(db_client=None) -> VectorSearchTool:
    """Get or create vector search tool"""
    global _vector_search_tool
    if _vector_search_tool is None:
        _vector_search_tool = VectorSearchTool(db_client)
    return _vector_search_tool

