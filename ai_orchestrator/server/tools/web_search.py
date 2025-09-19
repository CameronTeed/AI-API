import os
import httpx
import logging
from typing import Dict, Any, List, Optional
from ..schemas import WebSearchResult

logger = logging.getLogger(__name__)

class WebSearchClient:
    def __init__(self):
        self.provider = os.getenv('SEARCH_PROVIDER', 'serpapi')
        self.api_key = os.getenv('SEARCH_API_KEY')
        
        if not self.api_key:
            logger.warning("No SEARCH_API_KEY provided, web search will be limited")

    async def web_search(self, query: str, city: Optional[str] = None) -> Dict[str, Any]:
        """Perform web search using configured provider"""
        
        if not self.api_key:
            return {
                "results": [],
                "error": "No search API key configured"
            }

        # Enhance query with city if provided
        if city:
            enhanced_query = f"{query} {city}"
        else:
            enhanced_query = query

        try:
            if self.provider == 'serpapi':
                return await self._search_serpapi(enhanced_query)
            elif self.provider == 'bing':
                return await self._search_bing(enhanced_query)
            else:
                logger.error(f"Unknown search provider: {self.provider}")
                return {"results": [], "error": f"Unknown provider: {self.provider}"}
        
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {"results": [], "error": str(e)}

    async def _search_serpapi(self, query: str) -> Dict[str, Any]:
        """Search using SerpAPI"""
        url = "https://serpapi.com/search.json"
        
        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": "google",
            "gl": "ca",  # Canada locale
            "num": 3     # Top 3 results
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            results = []
            organic_results = data.get("organic_results", [])
            
            for result in organic_results[:3]:
                web_result = {
                    "title": result.get("title", ""),
                    "url": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "published_at": result.get("date")  # May not always be available
                }
                results.append(web_result)
            
            logger.info(f"SerpAPI returned {len(results)} results for query: {query}")
            return {"results": results}

    async def _search_bing(self, query: str) -> Dict[str, Any]:
        """Search using Bing Web Search API"""
        url = "https://api.bing.microsoft.com/v7.0/search"
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key
        }
        
        params = {
            "q": query,
            "count": 3,
            "mkt": "en-CA"  # Canada market
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            results = []
            web_pages = data.get("webPages", {}).get("value", [])
            
            for result in web_pages[:3]:
                web_result = {
                    "title": result.get("name", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("snippet", ""),
                    "published_at": result.get("dateLastCrawled")
                }
                results.append(web_result)
            
            logger.info(f"Bing returned {len(results)} results for query: {query}")
            return {"results": results}

# Global instance
_web_client = None

def get_web_client() -> WebSearchClient:
    """Get global web search client instance"""
    global _web_client
    if _web_client is None:
        _web_client = WebSearchClient()
    return _web_client
