"""
Consolidated Web Search Tool
Replaces both web_search.py and enhanced_web_search.py
"""

import logging
from typing import Dict, Any, List, Optional
from .base_tool import SearchTool

logger = logging.getLogger(__name__)


class WebSearchTool(SearchTool):
    """Unified web search tool"""
    
    def __init__(self, web_client=None):
        """Initialize web search tool"""
        super().__init__(
            name="web_search",
            description="Search the web for information"
        )
        self.web_client = web_client
        self._cache_ttl = 600  # 10 minutes
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute web search"""
        try:
            query = kwargs.get('query', '')
            limit = kwargs.get('limit', 5)
            
            if not query:
                return {'items': [], 'count': 0, 'success': False}
            
            if not self.web_client:
                logger.warning("Web client not available")
                return {'items': [], 'count': 0, 'success': False}
            
            # Use web client for search
            results = await self.web_client.web_search(query)
            items = results.get('items', [])[:limit]
            
            return {
                'items': items,
                'count': len(items),
                'success': True,
                'query': query
            }
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {'items': [], 'count': 0, 'success': False, 'error': str(e)}
    
    async def search_events(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """Search for events"""
        try:
            search_query = f"{query} events"
            if location:
                search_query += f" in {location}"
            
            results = await self.execute(query=search_query, limit=limit)
            
            # Filter for event-related results
            filtered = [
                item for item in results.get('items', [])
                if any(keyword in item.get('title', '').lower() 
                       for keyword in ['event', 'concert', 'show', 'festival', 'conference'])
            ]
            
            return {
                'items': filtered,
                'count': len(filtered),
                'success': True,
                'query': search_query
            }
        except Exception as e:
            logger.error(f"Event search error: {e}")
            return {'items': [], 'count': 0, 'success': False, 'error': str(e)}
    
    async def search_restaurants(
        self,
        cuisine: str,
        location: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """Search for restaurants"""
        try:
            search_query = f"{cuisine} restaurants"
            if location:
                search_query += f" in {location}"
            
            results = await self.execute(query=search_query, limit=limit)
            
            return {
                'items': results.get('items', []),
                'count': results.get('count', 0),
                'success': True,
                'cuisine': cuisine,
                'location': location
            }
        except Exception as e:
            logger.error(f"Restaurant search error: {e}")
            return {'items': [], 'count': 0, 'success': False, 'error': str(e)}


# Global instance
_web_search_tool = None


def get_web_search_tool(web_client=None) -> WebSearchTool:
    """Get or create web search tool"""
    global _web_search_tool
    if _web_search_tool is None:
        _web_search_tool = WebSearchTool(web_client)
    return _web_search_tool

