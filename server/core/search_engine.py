"""
Unified Search Engine
Combines vector search, web search, and ML-based filtering
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from .ml_integration import get_ml_wrapper

logger = logging.getLogger(__name__)


class SearchEngine:
    """Unified search engine combining multiple search strategies"""
    
    def __init__(self, vector_store=None, web_client=None):
        """Initialize search engine"""
        self.vector_store = vector_store
        self.web_client = web_client
        self.ml_wrapper = get_ml_wrapper()
        logger.info("✅ SearchEngine initialized")
    
    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search using semantic similarity"""
        if not self.vector_store:
            logger.warning("Vector store not available")
            return []

        try:
            # Note: vector_store.search is synchronous, not async
            # Build search parameters
            search_params = {'query': query, 'top_k': limit}
            if filters:
                search_params.update(filters)

            results = self.vector_store.search(**search_params)

            # Enrich results with vibe predictions
            for result in results:
                if 'title' in result and 'description' in result:
                    text = f"{result['title']} {result['description']}"
                    result['predicted_vibe'] = self.ml_wrapper.predict_vibe(text)

            return results
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []
    
    async def web_search(
        self,
        query: str,
        limit: int = 5,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search the web"""
        if not self.web_client:
            logger.warning("Web client not available")
            return []
        
        try:
            results = await self.web_client.web_search(query)
            return results.get('items', [])[:limit]
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return []
    
    async def hybrid_search(
        self,
        query: str,
        semantic_weight: float = 0.7,
        web_weight: float = 0.3,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Combine semantic and web search results"""
        try:
            # Run both searches in parallel
            semantic_results, web_results = await asyncio.gather(
                self.semantic_search(query, limit=int(limit * semantic_weight)),
                self.web_search(query, limit=int(limit * web_weight))
            )
            
            # Combine and deduplicate
            combined = semantic_results + web_results
            seen = set()
            unique = []
            
            for result in combined:
                key = result.get('title', result.get('name', ''))
                if key not in seen:
                    seen.add(key)
                    unique.append(result)
            
            return unique[:limit]
        except Exception as e:
            logger.error(f"Hybrid search error: {e}")
            return []
    
    async def vibe_filtered_search(
        self,
        query: str,
        target_vibes: List[str],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search and filter by target vibes"""
        try:
            # Fetch more results to ensure we get good matches even if they're not top-ranked
            results = await self.semantic_search(query, limit=limit * 5)
            logger.info(f"🔍 Semantic search returned {len(results)} results for query: '{query}'")

            if results:
                logger.info(f"📊 Top results: {[r.get('title', 'Unknown') for r in results[:3]]}")
                logger.info(f"📊 Vibes: {[r.get('predicted_vibe', 'Unknown') for r in results[:3]]}")

            # Filter by vibe - be more lenient
            # First try exact vibe matches
            filtered = [
                r for r in results
                if any(vibe.lower() in r.get('predicted_vibe', '').lower() for vibe in target_vibes)
            ]

            logger.info(f"✅ Found {len(filtered)} venues with exact vibe match for {target_vibes}")

            # If no exact matches, return all semantic results (vibe is just a hint, not a hard filter)
            if not filtered:
                logger.info(f"⚠️  No exact vibe matches for {target_vibes}, returning all {len(results)} semantic results")
                filtered = results

            return filtered[:limit]
        except Exception as e:
            logger.error(f"Vibe-filtered search error: {e}")
            return []


# Global instance
_search_engine = None


def get_search_engine(vector_store=None, web_client=None) -> SearchEngine:
    """Get or create search engine instance"""
    global _search_engine

    # If parameters are provided, always reinitialize (important for proper initialization)
    if vector_store is not None or web_client is not None:
        _search_engine = SearchEngine(vector_store, web_client)
        logger.info(f"🔄 SearchEngine reinitialized with vector_store={vector_store is not None}, web_client={web_client is not None}")
    elif _search_engine is None:
        # Only create default instance if no parameters provided and no instance exists
        _search_engine = SearchEngine(vector_store, web_client)
        logger.info("🆕 SearchEngine created with default parameters")

    return _search_engine

