"""
ML-Enhanced Chat Handler
Extends EnhancedChatHandler with ML service integration for vibe prediction and date planning
"""

import logging
from typing import Dict, Any, Optional, List
from .chat_handler import EnhancedChatHandler
from .core.ml_integration import get_ml_wrapper
from .core.chat_engine import get_chat_engine

logger = logging.getLogger(__name__)


class MLEnhancedChatHandler(EnhancedChatHandler):
    """Chat handler with integrated ML service for vibe prediction and date planning"""
    
    def __init__(self):
        """Initialize ML-enhanced chat handler"""
        super().__init__()
        
        # Initialize ML components
        self.ml_wrapper = get_ml_wrapper()
        self.chat_engine = get_chat_engine(self.llm_engine, self.agent_tools)
        
        logger.info("✅ ML-Enhanced ChatHandler initialized")
    
    def _extract_vibe_constraints(self, messages: List[Dict[str, str]]) -> Optional[List[str]]:
        """Extract vibe preferences from user messages"""
        try:
            if not messages:
                return None
            
            # Get the last user message
            user_message = None
            for msg in reversed(messages):
                if msg.get('role') == 'user':
                    user_message = msg.get('content', '')
                    break
            
            if not user_message:
                return None
            
            # Predict vibes from user message
            vibe = self.ml_wrapper.predict_vibe(user_message)
            return vibe.split(', ') if vibe else None
        except Exception as e:
            logger.warning(f"Error extracting vibe constraints: {e}")
            return None
    
    def _extract_planning_preferences(self, constraints: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Extract date planning preferences from constraints"""
        try:
            if not constraints:
                return None
            
            preferences = {}
            
            # Extract vibe
            if 'vibe' in constraints:
                preferences['vibe'] = constraints['vibe']
            
            # Extract budget
            if 'budget' in constraints:
                preferences['budget'] = constraints['budget']
            
            # Extract duration
            if 'duration' in constraints:
                preferences['duration'] = constraints['duration']
            
            # Extract location
            if 'location' in constraints:
                preferences['location'] = constraints['location']
            
            # Extract algorithm preference
            preferences['algorithm'] = constraints.get('algorithm', 'heuristic')
            
            return preferences if preferences else None
        except Exception as e:
            logger.warning(f"Error extracting planning preferences: {e}")
            return None
    
    async def _enhanced_vector_search_wrapper(self, **kwargs):
        """Enhanced vector search with vibe filtering"""
        try:
            query = kwargs.get('query', '')
            limit = kwargs.get('limit', 10)
            
            # Extract vibes from query
            vibes = self.ml_wrapper.predict_vibe(query).split(', ')
            
            # Search with vibe filtering
            results = await self.chat_engine.search_engine.vibe_filtered_search(
                query, vibes, limit
            )
            
            logger.info(f"🎯 ML-enhanced search returned {len(results)} results with vibes: {vibes}")
            return {"items": results, "source": "ml_enhanced_vector_search", "vibes": vibes}
        except Exception as e:
            logger.warning(f"ML-enhanced search error: {e}")
            # Fallback to regular search
            return await self._vector_search_wrapper(**kwargs)
    
    async def _date_planning_tool(self, **kwargs) -> Dict[str, Any]:
        """Tool for date planning using ML service"""
        try:
            preferences = kwargs.get('preferences', {})
            algorithm = kwargs.get('algorithm', 'heuristic')
            
            plan = self.ml_wrapper.plan_date(preferences, algorithm)
            
            if plan:
                logger.info(f"✅ Date plan generated using {algorithm} algorithm")
                return {
                    'success': True,
                    'plan': plan,
                    'algorithm': algorithm
                }
            else:
                logger.warning("Date planning returned no results")
                return {
                    'success': False,
                    'error': 'Could not generate date plan'
                }
        except Exception as e:
            logger.error(f"Date planning error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

