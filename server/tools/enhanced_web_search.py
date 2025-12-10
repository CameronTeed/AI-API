"""
Enhanced web search service with improved result ranking, caching, and content enrichment
"""
import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
import httpx
from urllib.parse import urlparse, urljoin
import re

from ..db_config import get_db_config

logger = logging.getLogger(__name__)

@dataclass
class EnhancedSearchResult:
    """Enhanced search result with additional metadata"""
    title: str
    url: str
    snippet: str
    source: str  # 'serpapi', 'bing', etc.
    published_at: Optional[str] = None
    domain: Optional[str] = None
    relevance_score: float = 0.0
    quality_score: float = 0.0
    combined_score: float = 0.0
    categories: List[str] = None
    location_mentions: List[str] = None
    price_mentions: List[str] = None
    extracted_metadata: Dict[str, Any] = None
    cached_at: Optional[datetime] = None

@dataclass
class SearchQuery:
    """Structured search query with context"""
    query: str
    city: Optional[str] = None
    categories: List[str] = None
    max_price: Optional[float] = None
    location_context: Optional[Dict[str, Any]] = None
    user_preferences: Optional[Dict[str, Any]] = None

class EnhancedWebSearchService:
    """Enhanced web search service with multiple providers, caching, and result enrichment"""
    
    def __init__(self):
        self.db_config = None
        self.providers = {
            'serpapi': self._search_serpapi,
            'bing': self._search_bing,
            'duckduckgo': self._search_duckduckgo
        }
        self.cache_ttl_hours = 24
        self.max_results_per_provider = 5
        
        # Content extraction patterns
        self.price_patterns = [
            r'\$\d+(?:\.\d{2})?',
            r'\d+\s*(?:dollars?|CAD|USD)',
            r'(?:from|starting at|only)\s*\$?\d+',
            r'free(?:\s+(?:admission|entry))?',
        ]
        
        self.location_patterns = [
            r'\b(?:downtown|uptown|midtown)\b',
            r'\b(?:north|south|east|west)(?:\s+end|\s+side)?\b',
            r'\b\d+\s+[A-Za-z\s]+(?:street|st|avenue|ave|road|rd|blvd|boulevard)\b',
            r'\b[A-Za-z\s]+(?:district|neighborhood|area|quarter)\b'
        ]
        
        self.category_keywords = {
            'romantic': ['romantic', 'date', 'couples', 'intimate', 'cozy'],
            'adventure': ['adventure', 'outdoor', 'hiking', 'kayak', 'climb'],
            'cultural': ['museum', 'gallery', 'theater', 'opera', 'concert'],
            'food': ['restaurant', 'dining', 'food', 'cuisine', 'chef'],
            'entertainment': ['show', 'movie', 'comedy', 'live music', 'performance'],
            'sports': ['sports', 'game', 'stadium', 'hockey', 'baseball', 'soccer'],
            'nightlife': ['bar', 'club', 'nightlife', 'cocktail', 'lounge'],
            'shopping': ['shopping', 'market', 'boutique', 'mall', 'store'],
            'nature': ['park', 'garden', 'beach', 'lake', 'forest', 'trail']
        }
    
    async def initialize(self):
        """Initialize the enhanced web search service"""
        self.db_config = get_db_config()
        await self._create_cache_table()
        logger.info("Enhanced web search service initialized")
    
    async def _create_cache_table(self):
        """Create cache table for search results"""
        def create_table():
            with self.db_config.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS search_result_cache (
                            cache_id SERIAL PRIMARY KEY,
                            query_hash VARCHAR(64) UNIQUE NOT NULL,
                            query_text TEXT NOT NULL,
                            results JSONB NOT NULL,
                            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP NOT NULL,
                            hit_count INTEGER DEFAULT 1,
                            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        
                        CREATE INDEX IF NOT EXISTS idx_search_cache_hash ON search_result_cache (query_hash);
                        CREATE INDEX IF NOT EXISTS idx_search_cache_expires ON search_result_cache (expires_at);
                    """)
                    conn.commit()
        
        # Run in thread since it's sync
        await asyncio.get_event_loop().run_in_executor(None, create_table)
    
    async def enhanced_search(self, search_query: SearchQuery) -> Dict[str, Any]:
        """Perform enhanced web search with multiple providers and result enrichment"""
        if not self.db_config:
            await self.initialize()
        
        # Generate cache key
        cache_key = self._generate_cache_key(search_query)
        
        # Try to get from cache first
        cached_results = await self._get_cached_results(cache_key)
        if cached_results:
            logger.info(f"Returning cached results for query: {search_query.query}")
            return cached_results
        
        # Perform search across multiple providers
        all_results = []
        errors = []
        
        # Build enhanced query
        enhanced_query = self._build_enhanced_query(search_query)
        
        # Search with multiple providers
        provider_tasks = []
        for provider_name, provider_func in self.providers.items():
            if self._is_provider_available(provider_name):
                provider_tasks.append(self._search_with_provider(provider_name, provider_func, enhanced_query))
        
        # Execute searches in parallel
        if provider_tasks:
            provider_results = await asyncio.gather(*provider_tasks, return_exceptions=True)
            
            for i, result in enumerate(provider_results):
                if isinstance(result, Exception):
                    provider_name = list(self.providers.keys())[i]
                    errors.append(f"{provider_name}: {str(result)}")
                else:
                    all_results.extend(result)
        
        # Deduplicate and enrich results
        deduplicated_results = self._deduplicate_results(all_results)
        enriched_results = await self._enrich_search_results(deduplicated_results, search_query)
        
        # Rank and score results
        ranked_results = self._rank_and_score_results(enriched_results, search_query)
        
        # Prepare final response
        final_results = {
            "query": asdict(search_query),
            "results": ranked_results[:15],  # Top 15 results
            "total_found": len(ranked_results),
            "providers_used": [name for name in self.providers.keys() if self._is_provider_available(name)],
            "errors": errors,
            "cached": False,
            "timestamp": datetime.now().isoformat()
        }
        
        # Cache the results
        await self._cache_results(cache_key, search_query.query, final_results)
        
        logger.info(f"Enhanced search completed: {len(ranked_results)} results for '{search_query.query}'")
        return final_results
    
    def _generate_cache_key(self, search_query: SearchQuery) -> str:
        """Generate cache key for search query"""
        query_str = json.dumps(asdict(search_query), sort_keys=True)
        return hashlib.sha256(query_str.encode()).hexdigest()
    
    async def _get_cached_results(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached search results"""
        def get_from_cache():
            with self.db_config.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE search_result_cache 
                        SET hit_count = hit_count + 1, last_accessed = CURRENT_TIMESTAMP
                        WHERE query_hash = %s AND expires_at > CURRENT_TIMESTAMP
                        RETURNING results
                        """,
                        (cache_key,)
                    )
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        cached_data = result[0]
                        cached_data["cached"] = True
                        return cached_data
            return None
        
        return await asyncio.get_event_loop().run_in_executor(None, get_from_cache)
    
    async def _cache_results(self, cache_key: str, query_text: str, results: Dict[str, Any]):
        """Cache search results"""
        expires_at = datetime.now() + timedelta(hours=self.cache_ttl_hours)
        
        def cache_results():
            with self.db_config.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO search_result_cache (query_hash, query_text, results, expires_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (query_hash) DO UPDATE SET
                            results = EXCLUDED.results,
                            cached_at = CURRENT_TIMESTAMP,
                            expires_at = EXCLUDED.expires_at,
                            hit_count = search_result_cache.hit_count + 1
                        """,
                        (cache_key, query_text, json.dumps(results), expires_at)
                    )
                    conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, cache_results)
    
    def _build_enhanced_query(self, search_query: SearchQuery) -> str:
        """Build enhanced search query with context"""
        query_parts = [search_query.query]
        
        if search_query.city:
            query_parts.append(f'"{search_query.city}"')
        
        if search_query.categories:
            # Add category keywords
            for category in search_query.categories:
                if category.lower() in self.category_keywords:
                    query_parts.append(self.category_keywords[category.lower()][0])
        
        # Add location-specific terms
        query_parts.append("things to do")
        
        return " ".join(query_parts)
    
    def _is_provider_available(self, provider_name: str) -> bool:
        """Check if a search provider is available and configured"""
        import os
        
        if provider_name == 'serpapi':
            return bool(os.getenv('SERPAPI_API_KEY'))
        elif provider_name == 'bing':
            return bool(os.getenv('BING_SEARCH_API_KEY'))
        elif provider_name == 'duckduckgo':
            return True  # DuckDuckGo doesn't require API key
        
        return False
    
    async def _search_with_provider(self, provider_name: str, provider_func, query: str) -> List[EnhancedSearchResult]:
        """Search with a specific provider"""
        try:
            results = await provider_func(query)
            
            enhanced_results = []
            for result in results:
                enhanced_result = EnhancedSearchResult(
                    title=result.get('title', ''),
                    url=result.get('url', ''),
                    snippet=result.get('snippet', ''),
                    source=provider_name,
                    published_at=result.get('published_at'),
                    domain=self._extract_domain(result.get('url', ''))
                )
                enhanced_results.append(enhanced_result)
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Error searching with {provider_name}: {e}")
            raise
    
    async def _search_serpapi(self, query: str) -> List[Dict[str, Any]]:
        """Search using SerpAPI"""
        import os
        api_key = os.getenv('SERPAPI_API_KEY')
        if not api_key:
            raise ValueError("SERPAPI_API_KEY not configured")
        
        url = "https://serpapi.com/search.json"
        params = {
            "q": query,
            "api_key": api_key,
            "engine": "google",
            "gl": "ca",
            "num": self.max_results_per_provider
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for result in data.get("organic_results", [])[:self.max_results_per_provider]:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "published_at": result.get("date")
                })
            
            return results
    
    async def _search_bing(self, query: str) -> List[Dict[str, Any]]:
        """Search using Bing Web Search API"""
        import os
        api_key = os.getenv('BING_SEARCH_API_KEY')
        if not api_key:
            raise ValueError("BING_SEARCH_API_KEY not configured")
        
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {
            "q": query,
            "count": self.max_results_per_provider,
            "mkt": "en-CA"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for result in data.get("webPages", {}).get("value", [])[:self.max_results_per_provider]:
                results.append({
                    "title": result.get("name", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("snippet", ""),
                    "published_at": result.get("dateLastCrawled")
                })
            
            return results
    
    async def _search_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo (simplified implementation)"""
        # Note: This is a placeholder. DuckDuckGo doesn't have a public API
        # In practice, you might use web scraping or alternative methods
        logger.info("DuckDuckGo search not implemented yet")
        return []
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return ""
    
    def _deduplicate_results(self, results: List[EnhancedSearchResult]) -> List[EnhancedSearchResult]:
        """Remove duplicate results based on URL and title similarity"""
        seen_urls = set()
        seen_titles = set()
        deduplicated = []
        
        for result in results:
            # Check URL duplication
            if result.url in seen_urls:
                continue
            
            # Check title similarity (simple implementation)
            title_lower = result.title.lower()
            is_similar_title = any(
                self._calculate_similarity(title_lower, existing_title) > 0.8 
                for existing_title in seen_titles
            )
            
            if is_similar_title:
                continue
            
            seen_urls.add(result.url)
            seen_titles.add(title_lower)
            deduplicated.append(result)
        
        return deduplicated
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity (Jaccard similarity)"""
        set1 = set(text1.split())
        set2 = set(text2.split())
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        return len(intersection) / len(union) if union else 0.0
    
    async def _enrich_search_results(self, results: List[EnhancedSearchResult], search_query: SearchQuery) -> List[EnhancedSearchResult]:
        """Enrich search results with additional metadata"""
        for result in results:
            # Extract price mentions
            result.price_mentions = self._extract_price_mentions(result.title + " " + result.snippet)
            
            # Extract location mentions
            result.location_mentions = self._extract_location_mentions(result.title + " " + result.snippet)
            
            # Categorize result
            result.categories = self._categorize_result(result.title + " " + result.snippet)
            
            # Calculate quality score
            result.quality_score = self._calculate_quality_score(result)
            
            # Calculate relevance score
            result.relevance_score = self._calculate_relevance_score(result, search_query)
        
        return results
    
    def _extract_price_mentions(self, text: str) -> List[str]:
        """Extract price mentions from text"""
        prices = []
        for pattern in self.price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            prices.extend(matches)
        return list(set(prices))  # Remove duplicates
    
    def _extract_location_mentions(self, text: str) -> List[str]:
        """Extract location mentions from text"""
        locations = []
        for pattern in self.location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            locations.extend(matches)
        return list(set(locations))  # Remove duplicates
    
    def _categorize_result(self, text: str) -> List[str]:
        """Categorize result based on keywords"""
        text_lower = text.lower()
        categories = []
        
        for category, keywords in self.category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                categories.append(category)
        
        return categories
    
    def _calculate_quality_score(self, result: EnhancedSearchResult) -> float:
        """Calculate quality score for a result"""
        score = 0.0
        
        # Title quality (length and readability)
        if 10 <= len(result.title) <= 80:
            score += 0.2
        
        # Snippet quality
        if 50 <= len(result.snippet) <= 300:
            score += 0.2
        
        # Domain reputation (simple heuristic)
        trusted_domains = ['yelp.com', 'tripadvisor.com', 'timeout.com', 'blogto.com']
        if any(domain in result.domain for domain in trusted_domains):
            score += 0.3
        
        # Has price information
        if result.price_mentions:
            score += 0.1
        
        # Has location information
        if result.location_mentions:
            score += 0.1
        
        # Published date (newer is better)
        if result.published_at:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_relevance_score(self, result: EnhancedSearchResult, search_query: SearchQuery) -> float:
        """Calculate relevance score for a result"""
        score = 0.0
        text = (result.title + " " + result.snippet).lower()
        query_words = search_query.query.lower().split()
        
        # Query word matching
        matched_words = sum(1 for word in query_words if word in text)
        score += (matched_words / len(query_words)) * 0.4
        
        # City matching
        if search_query.city and search_query.city.lower() in text:
            score += 0.3
        
        # Category matching
        if search_query.categories:
            category_matches = sum(1 for cat in search_query.categories if cat in result.categories)
            score += (category_matches / len(search_query.categories)) * 0.2
        
        # Price relevance
        if search_query.max_price and result.price_mentions:
            # Simple heuristic: if any price mention is under max_price
            score += 0.1
        
        return min(score, 1.0)
    
    def _rank_and_score_results(self, results: List[EnhancedSearchResult], search_query: SearchQuery) -> List[Dict[str, Any]]:
        """Rank and score results"""
        for result in results:
            # Combined score (weighted average)
            result.combined_score = (
                result.relevance_score * 0.6 + 
                result.quality_score * 0.4
            )
        
        # Sort by combined score
        results.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Convert to dict format for JSON serialization
        return [asdict(result) for result in results]
    
    async def clear_expired_cache(self) -> int:
        """Clear expired cache entries"""
        if not self.db_config:
            await self.initialize()
        
        def clear_cache():
            with self.db_config.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM search_result_cache WHERE expires_at <= CURRENT_TIMESTAMP"
                    )
                    count = cursor.rowcount
                    conn.commit()
                    return count
        
        return await asyncio.get_event_loop().run_in_executor(None, clear_cache)
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache usage statistics"""
        if not self.db_config:
            await self.initialize()
        
        def get_stats():
            with self.db_config.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT 
                            COUNT(*) as total_entries,
                            COUNT(*) FILTER (WHERE expires_at > CURRENT_TIMESTAMP) as active_entries,
                            SUM(hit_count) as total_hits,
                            AVG(hit_count) as avg_hits_per_entry,
                            MIN(cached_at) as oldest_entry,
                            MAX(last_accessed) as most_recent_access
                        FROM search_result_cache
                        """
                    )
                    
                    result = cursor.fetchone()
                    if result:
                        total, active, total_hits, avg_hits, oldest, recent = result
                        return {
                            "total_entries": total,
                            "active_entries": active,
                            "expired_entries": total - active,
                            "total_cache_hits": total_hits or 0,
                            "avg_hits_per_entry": round(float(avg_hits) if avg_hits else 0, 2),
                            "oldest_entry": oldest.isoformat() if oldest else None,
                            "most_recent_access": recent.isoformat() if recent else None
                        }
            return {}
        
        return await asyncio.get_event_loop().run_in_executor(None, get_stats)

# Global enhanced web search service instance
_enhanced_search_service = None

async def get_enhanced_search_service() -> EnhancedWebSearchService:
    """Get global enhanced web search service instance"""
    global _enhanced_search_service
    if _enhanced_search_service is None:
        _enhanced_search_service = EnhancedWebSearchService()
        await _enhanced_search_service.initialize()
    return _enhanced_search_service