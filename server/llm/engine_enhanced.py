"""
Enhanced LLM Engine
Wrapper around the original engine that leverages new core services
"""

import logging
from typing import AsyncIterator, List, Dict, Any, Optional, Callable
from .engine import LLMEngine
from ..core.ml_integration import get_ml_wrapper
from ..core.search_engine import get_search_engine

logger = logging.getLogger(__name__)


class EnhancedLLMEngine:
    """Enhanced LLM engine that leverages new core services"""
    
    def __init__(self):
        """Initialize enhanced LLM engine"""
        self.engine = LLMEngine()
        self.ml_wrapper = get_ml_wrapper()
        self.search_engine = get_search_engine()
        logger.info("✅ EnhancedLLMEngine initialized with core services")
    
    async def run_chat(
        self,
        messages: List[Dict[str, str]],
        vector_search_func: Optional[Callable] = None,
        web_search_func: Optional[Callable] = None,
        agent_tools: Optional[Any] = None,
        session_id: Optional[str] = None,
        constraints: Optional[Dict] = None,
        user_location: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        """
        Run chat with enhanced ML integration
        
        Automatically:
        - Predicts vibes from user messages
        - Filters search results by vibe
        - Integrates date planning
        """
        try:
            # Extract vibe from last user message
            vibe = None
            if messages:
                for msg in reversed(messages):
                    if msg.get('role') == 'user':
                        vibe = self.ml_wrapper.predict_vibe(msg.get('content', ''))
                        logger.debug(f"Predicted vibe: {vibe}")
                        break
            
            # Create enhanced search function with vibe filtering
            async def enhanced_vector_search(**kwargs):
                """Vector search with vibe filtering"""
                query = kwargs.get('query', '')
                limit = kwargs.get('limit', 10)
                
                if vibe:
                    vibes = vibe.split(', ')
                    results = await self.search_engine.vibe_filtered_search(
                        query, vibes, limit
                    )
                else:
                    results = await self.search_engine.semantic_search(query, limit)
                
                return {"items": results, "source": "enhanced_vector_search"}
            
            # Create enhanced web search function
            async def enhanced_web_search(**kwargs):
                """Web search with vibe context"""
                query = kwargs.get('query', '')
                limit = kwargs.get('limit', 5)
                
                results = await self.search_engine.web_search(query, limit)
                return {"items": results, "source": "enhanced_web_search"}
            
            # Use provided functions or enhanced versions
            vector_search = vector_search_func or enhanced_vector_search
            web_search = web_search_func or enhanced_web_search
            
            # Run original engine with enhanced search
            async for chunk in self.engine.run_chat(
                messages=messages,
                vector_search_func=vector_search,
                web_search_func=web_search,
                agent_tools=agent_tools,
                session_id=session_id,
                constraints=constraints,
                user_location=user_location
            ):
                yield chunk
        
        except Exception as e:
            logger.error(f"Enhanced chat error: {e}")
            yield f"Error: {str(e)}"


# Global instance
_enhanced_engine = None


def get_enhanced_llm_engine() -> EnhancedLLMEngine:
    """Get or create enhanced LLM engine"""
    global _enhanced_engine
    if _enhanced_engine is None:
        _enhanced_engine = EnhancedLLMEngine()
    return _enhanced_engine

