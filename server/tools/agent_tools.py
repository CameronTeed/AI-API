"""
Simplified Agent Tools for AI Chat System
Provides only essential tools: vector search, web search, and basic utilities
Removed: Google Places, ScrapingBee, Nominatim, Eventbrite (not used in optimized flow)
"""

import os
import logging
from typing import Dict, Any, List, Optional
from .vector_search import get_vector_store
from .web_search import WebSearchClient

logger = logging.getLogger(__name__)


class AgentToolsManager:
    """Simplified agent tools manager - only essential tools for GA-optimized flow"""
    
    def __init__(self):
        logger.debug("🔧 Initializing Simplified AgentToolsManager")
        
        # Initialize only essential services
        self.web_client = WebSearchClient()
        self.vector_store = get_vector_store()
        
        # Tool cache for performance
        self._tool_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        logger.info("✅ Simplified AgentToolsManager initialized (vector search + web search only)")
    
    async def vector_search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search vector database for venues"""
        try:
            results = self.vector_store.search(query, top_k=limit)
            return {
                'success': True,
                'results': results,
                'count': len(results)
            }
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def web_search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search the web for information"""
        try:
            results = await self.web_client.web_search(query)
            items = results.get('items', [])[:limit]
            return {
                'success': True,
                'results': items,
                'count': len(items)
            }
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_tool_list(self) -> List[str]:
        """Get list of available tools"""
        return [
            'vector_search',
            'web_search'
        ]
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name"""
        if tool_name == 'vector_search':
            return await self.vector_search(**kwargs)
        elif tool_name == 'web_search':
            return await self.web_search(**kwargs)
        else:
            return {'success': False, 'error': f'Unknown tool: {tool_name}'}


def get_agent_tools() -> AgentToolsManager:
    """Get or create agent tools instance"""
    return AgentToolsManager()

