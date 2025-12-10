"""
Enhanced Agent Tools Manager
Wrapper around original agent tools that uses consolidated tools and ML service
"""

import logging
from typing import Dict, Any, Optional
from .agent_tools import AgentToolsManager
from .consolidated_vector_search import get_vector_search_tool
from .consolidated_web_search import get_web_search_tool
from ..core.ml_integration import get_ml_wrapper

logger = logging.getLogger(__name__)


class EnhancedAgentToolsManager:
    """Enhanced agent tools manager using consolidated tools"""
    
    def __init__(self):
        """Initialize enhanced agent tools"""
        self.original_tools = AgentToolsManager()
        self.vector_search_tool = get_vector_search_tool()
        self.web_search_tool = get_web_search_tool()
        self.ml_wrapper = get_ml_wrapper()
        logger.info("✅ EnhancedAgentToolsManager initialized")
    
    async def search_venues(
        self,
        query: str,
        location: Optional[Dict[str, float]] = None,
        limit: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """Search for venues using consolidated vector search"""
        try:
            # Predict vibe from query
            vibe = self.ml_wrapper.predict_vibe(query)
            vibes = vibe.split(', ') if vibe else []
            
            # Use vector search tool with vibe filtering
            if vibes:
                results = await self.vector_search_tool.search_by_vibe(
                    vibes=vibes,
                    limit=limit
                )
            else:
                results = await self.vector_search_tool.execute(
                    query=query,
                    limit=limit
                )
            
            return results
        except Exception as e:
            logger.error(f"Venue search error: {e}")
            return {'results': [], 'count': 0, 'success': False}
    
    async def search_web(
        self,
        query: str,
        limit: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        """Search the web using consolidated web search"""
        try:
            results = await self.web_search_tool.execute(
                query=query,
                limit=limit
            )
            return results
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {'items': [], 'count': 0, 'success': False}
    
    async def search_events(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """Search for events using web search"""
        try:
            results = await self.web_search_tool.search_events(
                query=query,
                location=location,
                limit=limit
            )
            return results
        except Exception as e:
            logger.error(f"Event search error: {e}")
            return {'items': [], 'count': 0, 'success': False}
    
    async def search_restaurants(
        self,
        cuisine: str,
        location: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """Search for restaurants using web search"""
        try:
            results = await self.web_search_tool.search_restaurants(
                cuisine=cuisine,
                location=location,
                limit=limit
            )
            return results
        except Exception as e:
            logger.error(f"Restaurant search error: {e}")
            return {'items': [], 'count': 0, 'success': False}
    
    # Delegate other methods to original tools
    def __getattr__(self, name):
        """Delegate unknown methods to original tools"""
        return getattr(self.original_tools, name)


# Global instance
_enhanced_tools = None


def get_enhanced_agent_tools() -> EnhancedAgentToolsManager:
    """Get or create enhanced agent tools"""
    global _enhanced_tools
    if _enhanced_tools is None:
        _enhanced_tools = EnhancedAgentToolsManager()
    return _enhanced_tools

