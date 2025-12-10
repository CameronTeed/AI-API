"""
Simplified Chat Engine
Refactored from llm/engine.py with ML service integration
"""

import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from .ml_integration import get_ml_wrapper
from .search_engine import get_search_engine

logger = logging.getLogger(__name__)


class ChatEngine:
    """Simplified chat engine with ML integration"""
    
    def __init__(self, llm_engine=None, agent_tools=None):
        """Initialize chat engine"""
        self.llm_engine = llm_engine
        self.agent_tools = agent_tools
        self.ml_wrapper = get_ml_wrapper()
        self.search_engine = get_search_engine()
        logger.info("✅ ChatEngine initialized")
    
    async def process_chat(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
        constraints: Optional[Dict] = None,
        user_location: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        """Process chat with ML integration"""
        
        if not self.llm_engine:
            logger.error("LLM engine not available")
            yield "Error: LLM engine not available"
            return
        
        try:
            # Analyze user intent for ML-based planning
            if constraints and 'vibe' in constraints:
                logger.debug(f"Vibe constraint detected: {constraints['vibe']}")
            
            # Run chat through LLM with enhanced tools
            async for chunk in self.llm_engine.run_chat(
                messages=messages,
                vector_search_func=self._vector_search_wrapper,
                web_search_func=self._web_search_wrapper,
                agent_tools=self.agent_tools,
                session_id=session_id,
                constraints=constraints,
                user_location=user_location
            ):
                yield chunk
        
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            yield f"Error: {str(e)}"
    
    async def _vector_search_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for vector search with ML filtering"""
        try:
            query = kwargs.get('query', '')
            limit = kwargs.get('limit', 10)
            target_vibes = kwargs.get('vibes', [])
            
            if target_vibes:
                results = await self.search_engine.vibe_filtered_search(
                    query, target_vibes, limit
                )
            else:
                results = await self.search_engine.semantic_search(query, limit)
            
            return {'results': results, 'count': len(results)}
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return {'results': [], 'count': 0}
    
    async def _web_search_wrapper(self, **kwargs) -> Dict[str, Any]:
        """Wrapper for web search"""
        try:
            query = kwargs.get('query', '')
            limit = kwargs.get('limit', 5)
            location = kwargs.get('location')
            
            results = await self.search_engine.web_search(query, limit, location)
            return {'items': results, 'count': len(results)}
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {'items': [], 'count': 0}
    
    def predict_vibe(self, text: str) -> str:
        """Predict vibe for text"""
        return self.ml_wrapper.predict_vibe(text)
    
    def plan_date(self, preferences: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Plan a date using ML service"""
        algorithm = preferences.get('algorithm', 'heuristic')
        return self.ml_wrapper.plan_date(preferences, algorithm)


# Global instance
_chat_engine = None


def get_chat_engine(llm_engine=None, agent_tools=None) -> ChatEngine:
    """Get or create chat engine instance"""
    global _chat_engine
    if _chat_engine is None:
        _chat_engine = ChatEngine(llm_engine, agent_tools)
    return _chat_engine

