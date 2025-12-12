"""
Web Search Tool - Consolidated implementation
Enhanced web search service with multiple providers, caching, and result enrichment.

This is the main web search implementation. All other web search files
(web_search.py, enhanced_web_search.py, consolidated_web_search.py)
are deprecated and should use this module instead.
"""

import logging
from typing import Dict, Any, Optional

# Import the actual implementation from enhanced_web_search
from .enhanced_web_search import EnhancedWebSearchService, get_enhanced_search_service

logger = logging.getLogger(__name__)


class WebSearchClient:
    """Consolidated web search client using enhanced service"""

    def __init__(self):
        self.service = EnhancedWebSearchService()
        logger.debug("✅ WebSearchClient initialized with EnhancedWebSearchService")

    async def web_search(self, query: str, city: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform web search using the enhanced service

        Args:
            query: Search query
            city: Optional city to filter results

        Returns:
            Dictionary with search results
        """
        try:
            # Use enhanced search service
            results = await self.service.search(query, city=city)

            # Convert to standard format
            return {
                "items": results,
                "source": "enhanced_web_search"
            }

        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {"items": [], "error": str(e)}


# Global instance
_web_client = None


def get_web_client() -> WebSearchClient:
    """Get global web search client instance"""
    global _web_client
    if _web_client is None:
        _web_client = WebSearchClient()
    return _web_client


# Export the main interface
__all__ = ['WebSearchClient', 'EnhancedWebSearchService', 'get_web_client', 'get_enhanced_search_service']

