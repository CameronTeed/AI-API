"""
Web search client - consolidated wrapper around enhanced web search service
"""

import logging
from typing import Dict, Any, Optional
from .enhanced_web_search import EnhancedWebSearchService

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
