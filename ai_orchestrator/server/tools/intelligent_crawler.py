"""
Intelligent Web Crawler for Date Ideas
Performs smart web searches and deep content extraction
"""

import asyncio
import logging
import json
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urljoin
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class IntelligentCrawler:
    """Smart web crawler that searches for relevant content and extracts useful information"""
    
    def __init__(self, scrapingbee_api_key: Optional[str] = None, serpapi_key: Optional[str] = None):
        self.scrapingbee_api_key = scrapingbee_api_key
        self.serpapi_key = serpapi_key
        
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            },
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        # Rate limiting
        self._request_delays = {}
        self._min_delay = 1.0  # Minimum 1 second between requests to same domain
        
        # Extraction patterns
        self.patterns = {
            'phone': [
                r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                r'\+1[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                r'tel:?\s*\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            ],
            'email': [
                r'[\w\.-]+@[\w\.-]+\.\w+',
                r'mailto:\s*[\w\.-]+@[\w\.-]+\.\w+'
            ],
            'price': [
                r'\$\d+(?:\.\d{2})?(?:\s*-\s*\$\d+(?:\.\d{2})?)?',
                r'from\s+\$\d+',
                r'starting\s+at\s+\$\d+',
                r'(?:only|just)\s+\$\d+',
                r'free(?:\s+(?:admission|entry|event))?'
            ],
            'hours': [
                r'(?:open|hours|schedule).*?(?:monday|mon|tuesday|tue|wednesday|wed|thursday|thu|friday|fri|saturday|sat|sunday|sun).*?(?:\d{1,2}(?::\d{2})?\s*(?:am|pm))',
                r'\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*-\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)',
                r'(?:open|closes?)\s*(?:daily|everyday)?\s*(?:at)?\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)'
            ],
            'address': [
                r'\d+\s+[A-Za-z0-9\s]+(?:street|st\.?|avenue|ave\.?|road|rd\.?|boulevard|blvd\.?|drive|dr\.?|lane|ln\.?|way|court|ct\.?)',
                r'\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}'
            ]
        }
    
    async def intelligent_search_and_extract(
        self, 
        query: str, 
        city: str = "Ottawa",
        max_results: int = 3,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform intelligent web search and extract relevant information
        
        Args:
            query: Search query (e.g., "romantic restaurants")
            city: City to search in
            max_results: Maximum number of results to process
            focus_areas: Specific areas to focus on (hours, menu, events, etc.)
        
        Returns:
            Dict with extracted information from multiple sources
        """
        logger.info(f"🔍 Intelligent search: '{query}' in {city}")
        
        if focus_areas is None:
            focus_areas = ['hours', 'contact', 'pricing', 'events', 'description']
        
        # Step 1: Perform web search to find relevant URLs
        search_results = await self._perform_web_search(query, city)
        
        if not search_results:
            logger.warning("No search results found")
            return {
                'success': False,
                'error': 'No search results found',
                'query': query,
                'city': city,
                'results_found': 0,
                'venues': []
            }
        
        # Step 2: Extract and visit relevant URLs
        extracted_data = []
        urls_to_visit = []
        
        for result in search_results[:max_results]:
            url = result.get('url', '')
            if url and self._is_relevant_url(url, query):
                urls_to_visit.append({
                    'url': url,
                    'title': result.get('title', ''),
                    'snippet': result.get('snippet', '')
                })
        
        if not urls_to_visit:
            logger.warning("No relevant URLs found after filtering")
            # Return search results as-is without extraction
            return {
                'success': True,
                'query': query,
                'city': city,
                'results_found': len(search_results),
                'venues': [{
                    'venue_name': r.get('title', ''),
                    'url': r.get('url', ''),
                    'description': r.get('snippet', ''),
                    'source': 'search_only'
                } for r in search_results[:max_results]],
                'timestamp': datetime.now().isoformat()
            }
        
        # Step 3: Crawl each URL and extract information (with error tolerance)
        scraping_errors = 0
        for url_info in urls_to_visit:
            logger.info(f"📄 Crawling: {url_info['url']}")
            
            try:
                extracted = await self.extract_venue_information(
                    url_info['url'],
                    venue_name=url_info['title'],
                    focus_areas=focus_areas
                )
                
                if extracted.get('success'):
                    extracted_data.append({
                        **extracted['data'],
                        'search_title': url_info['title'],
                        'search_snippet': url_info['snippet']
                    })
                else:
                    # Don't count timeouts as critical errors for official sites
                    error_msg = extracted.get('error', 'Unknown error')
                    if 'timeout' in error_msg.lower() and ('ottawa.ca' in url_info['url'] or '.gov' in url_info['url']):
                        logger.warning(f"Timeout on official site {url_info['url']} - keeping result anyway")
                    else:
                        scraping_errors += 1
                    
                    # If scraping fails, at least include search result
                    extracted_data.append({
                        'venue_name': url_info['title'],
                        'url': url_info['url'],
                        'description': url_info['snippet'],
                        'source': 'search_only',
                        'extraction_error': error_msg
                    })
            except Exception as e:
                logger.error(f"Error processing {url_info['url']}: {e}")
                scraping_errors += 1
                # Include search result even if extraction fails
                extracted_data.append({
                    'venue_name': url_info['title'],
                    'url': url_info['url'],
                    'description': url_info['snippet'],
                    'source': 'search_only'
                })
            
            # If too many scraping errors, stop trying (increased tolerance for government sites)
            if scraping_errors >= 5:
                logger.warning("Too many scraping errors, returning search results only")
                break
        
        return {
            'success': True,
            'query': query,
            'city': city,
            'results_found': len(extracted_data),
            'venues': extracted_data,
            'scraping_errors': scraping_errors,
            'timestamp': datetime.now().isoformat()
        }
    
    async def extract_venue_information(
        self,
        url: str,
        venue_name: Optional[str] = None,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract detailed information from a venue's website with multiple fallback methods
        """
        try:
            content = None
            extraction_method = None
            
            # Try ScrapingBee first (fastest for JS-heavy sites)
            content = await self._scrape_with_scrapingbee(url)
            if content:
                extraction_method = "scrapingbee_js"
            else:
                # Fallback to simplified ScrapingBee (no JS but more reliable than basic HTTP)
                logger.info(f"🔄 ScrapingBee JS failed for {url}, trying simplified ScrapingBee...")
                content = await self._scrape_simplified(url)
                if content:
                    extraction_method = "scrapingbee_simple"
                else:
                    # Last resort: basic HTTP (fastest but least reliable)
                    logger.info(f"🔄 ScrapingBee failed for {url}, trying basic HTTP...")
                    content = await self._scrape_basic(url)
                    if content:
                        extraction_method = "basic_http"
            
            if not content:
                return {
                    'success': False,
                    'error': 'All extraction methods failed',
                    'url': url
                }
            
            # Parse and extract content using BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract comprehensive venue information with date-planning focus
            extracted_info = {
                'venue_name': venue_name or self._extract_venue_name(soup),
                'url': url,
                'extraction_method': extraction_method,
                'description': self._extract_description(soup),
                'contact': self._extract_contact_info(soup, content),
                'hours': self._extract_hours(soup, content),
                'pricing': self._extract_pricing(soup, content),
                'events': self._extract_events(soup),
                'highlights': self._extract_highlights(soup, content),
                'sledding_specific': self._extract_sledding_info(soup, content),
                'images': self._extract_images(soup, url),  # New: Image extraction for visual appeal
                'date_planning': self._extract_date_planning_info(soup, content),  # New: Date-specific info
                'source': 'extracted'
            }
            
            return {
                'success': True,
                'data': extracted_info,
                'url': url,
                'extraction_method': extraction_method
            }
            
        except Exception as e:
            logger.error(f"Error extracting venue information from {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }
    
    async def _scrape_with_scrapingbee(self, url: str, timeout: int = 20) -> Optional[str]:
        """Scrape using ScrapingBee API with JavaScript rendering - optimized for speed"""
        try:
            params = {
                'api_key': self.scrapingbee_api_key,
                'url': url,
                'render_js': 'true',
                'wait': '2000',  # Reduced wait time for faster response
                'wait_for': 'domcontentloaded',  # Faster than networkidle2
                'block_resources': 'true',  # Block images/videos for faster loading
                'block_ads': 'true',  # Block ads
                'premium_proxy': 'false',
                'return_page_source': 'true'
            }
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
                response = await client.get(
                    "https://app.scrapingbee.com/api/v1/",
                    params=params
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ ScrapingBee successful for {url}")
                    # Check response quality
                    if len(response.text) < 500:
                        logger.warning(f"ScrapingBee returned suspiciously short content ({len(response.text)} chars)")
                    return response.text
                    
                elif response.status_code == 401:
                    logger.error("ScrapingBee authentication failed - invalid API key")
                    return None
                    
                elif response.status_code == 402:
                    logger.error("ScrapingBee quota exceeded")
                    return None
                
                elif response.status_code == 500:
                    logger.warning(f"ScrapingBee internal error for {url} - site may be blocking")
                    return None
                    
                elif response.status_code == 503:
                    logger.warning(f"ScrapingBee service unavailable for {url}")
                    return None
                    
                elif response.status_code == 422:
                    logger.error(f"ScrapingBee validation error for {url}")
                    # Try with simpler parameters
                    simple_params = {
                        'api_key': self.scrapingbee_api_key,
                        'url': url,
                        'render_js': 'false'
                    }
                    retry_response = await client.get(
                        "https://app.scrapingbee.com/api/v1/",
                        params=simple_params
                    )
                    if retry_response.status_code == 200:
                        return retry_response.text
                    return None
                    
                else:
                    logger.warning(f"ScrapingBee error {response.status_code}: {response.text[:200]}")
                    return None
                    
        except httpx.TimeoutException:
            logger.warning(f"ScrapingBee timeout for {url} (>{timeout}s) - using search result fallback")
            return None
            
        except Exception as e:
            logger.error(f"ScrapingBee error: {e}")
            return None

    async def _scrape_simplified(self, url: str, timeout: int = 10) -> Optional[str]:
        """
        Simplified scraping using ScrapingBee without JavaScript for faster results
        """
        if not self.scrapingbee_api_key:
            return None
            
        try:
            # Simplified parameters - no JavaScript, faster
            params = {
                'api_key': self.scrapingbee_api_key,
                'url': url,
                'render_js': 'false',  # No JavaScript for speed
                'block_resources': 'true',
                'block_ads': 'true',
                'return_page_source': 'true'
            }
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5.0)) as client:
                response = await client.get(
                    "https://app.scrapingbee.com/api/v1/",
                    params=params
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Simplified scraping successful for {url}")
                    return response.text
                else:
                    logger.warning(f"Simplified scraping failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.warning(f"Simplified scraping error: {e}")
            return None
    
    async def _scrape_basic(self, url: str, retry_count: int = 3) -> Optional[str]:
        """Basic web scraping with improved error handling and retries"""
        domain = urlparse(url).netloc
        
        # Rate limiting - wait if we recently scraped this domain
        if domain in self._request_delays:
            last_request = self._request_delays[domain]
            elapsed = asyncio.get_event_loop().time() - last_request
            if elapsed < self._min_delay:
                await asyncio.sleep(self._min_delay - elapsed)
        
        for attempt in range(retry_count):
            try:
                logger.debug(f"Scraping attempt {attempt + 1}/{retry_count} for {url}")
                
                response = await self.http_client.get(url)
                self._request_delays[domain] = asyncio.get_event_loop().time()
                
                response.raise_for_status()
                
                # Check if we got a valid HTML response
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                    logger.warning(f"Non-HTML content type: {content_type} for {url}")
                    if attempt < retry_count - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return None
                
                # Check for common anti-bot responses
                text = response.text
                if len(text) < 500 and any(indicator in text.lower() for indicator in ['captcha', 'blocked', 'access denied', 'cloudflare']):
                    logger.warning(f"Possible bot detection on {url}")
                    if attempt < retry_count - 1:
                        await asyncio.sleep(3 ** attempt)
                        continue
                    # Try ScrapingBee as fallback
                    if self.scrapingbee_api_key:
                        logger.info("Trying ScrapingBee due to bot detection")
                        return await self._scrape_with_scrapingbee(url)
                    return None
                
                return text
                
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error {e.response.status_code} for {url}")
                if e.response.status_code in [403, 429]:  # Forbidden or rate limited
                    if attempt < retry_count - 1:
                        await asyncio.sleep(5 * (attempt + 1))
                        continue
                    # Try ScrapingBee for difficult sites
                    if self.scrapingbee_api_key:
                        logger.info("Trying ScrapingBee due to HTTP error")
                        return await self._scrape_with_scrapingbee(url)
                return None
                
            except httpx.TimeoutException:
                logger.warning(f"Timeout scraping {url}, attempt {attempt + 1}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2)
                    continue
                return None
                
            except Exception as e:
                logger.error(f"Basic scraping error for {url}: {e}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2)
                    continue
                return None
        
        return None
    
    async def _perform_web_search(self, query: str, city: str) -> List[Dict[str, Any]]:
        """Perform web search using SerpAPI (Google) with fallback to DuckDuckGo"""
        
        # Try SerpAPI first (Google Search)
        if self.serpapi_key:
            results = await self._serpapi_search(query, city)
            if results:
                logger.info(f"Found {len(results)} results from SerpAPI (Google)")
                return results
        else:
            logger.warning("SerpAPI key not configured, using DuckDuckGo fallback")
        
        # Fallback to DuckDuckGo
        return await self._duckduckgo_search(query, city)
    
    async def _serpapi_search(self, query: str, city: str) -> List[Dict[str, Any]]:
        """Search using SerpAPI (Google Search API) - finds blogs, posts, articles"""
        try:
            from serpapi import GoogleSearch
            
            # Construct location-specific query
            if city.lower() == "ottawa":
                search_query = f"{query} {city} Ontario"
            else:
                search_query = f"{query} {city}"
            
            logger.info(f"🔍 SerpAPI Google search: {search_query}")
            
            # Configure SerpAPI search
            params = {
                "q": search_query,
                "api_key": self.serpapi_key,
                "engine": "google",
                "num": 20,  # Get 20 results
                "gl": "ca",  # Canada
                "hl": "en"   # English
            }
            
            # Run synchronous search in thread pool
            import asyncio
            loop = asyncio.get_event_loop()
            search = await loop.run_in_executor(None, lambda: GoogleSearch(params))
            results_data = await loop.run_in_executor(None, search.get_dict)
            
            results = []
            
            # Process organic results (main search results)
            organic_results = results_data.get('organic_results', [])
            logger.info(f"Got {len(organic_results)} organic results from Google")
            
            for result in organic_results:
                url = result.get('link', '')
                title = result.get('title', '')
                snippet = result.get('snippet', '')
                
                # Don't filter by city for every result - some blogs may not mention city explicitly
                # But prioritize those that do
                has_city = city.lower() in snippet.lower() or city.lower() in title.lower() or city.lower() in url.lower()
                
                # Check URL relevance - be more lenient for blogs and articles
                if url and self._is_relevant_url_for_content(url, query):
                    result_item = {
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'source': 'serpapi_google',
                        'has_city_mention': has_city
                    }
                    results.append(result_item)
            
            # Sort to prioritize results with city mentions
            results.sort(key=lambda x: x.get('has_city_mention', False), reverse=True)
            
            logger.info(f"SerpAPI found {len(results)} relevant results")
            return results[:15]  # Limit to top 15
            
        except ImportError:
            logger.error("SerpAPI library not installed: pip install google-search-results")
            return []
        except Exception as e:
            logger.error(f"SerpAPI search error: {e}")
            return []
    
    def _is_relevant_url_for_content(self, url: str, query: str) -> bool:
        """Check if URL is relevant for content like blogs, posts, articles"""
        # More lenient filtering for content discovery
        excluded_domains = [
            'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
            'google.com', 'youtube.com', 'pinterest.com',
            'zhihu.com', 'baidu.com', 'adultfriendfinder', 'dating'
        ]
        
        domain = urlparse(url).netloc.lower()
        url_lower = url.lower()
        
        # Exclude based on domain
        for excluded in excluded_domains:
            if excluded in domain:
                return False
        
        # Allow yelp, tripadvisor, reddit for content discovery
        # Allow blog indicators
        blog_indicators = ['blog', 'post', 'article', 'guide', 'review', 'best', 'top']
        if any(indicator in url_lower for indicator in blog_indicators):
            return True
        
        # Must be HTTPS
        if not url.startswith('https://'):
            return False
        
        return True
    
    async def _duckduckgo_search(self, query: str, city: str) -> List[Dict[str, Any]]:
        """Fallback search using DuckDuckGo"""
        try:
            from duckduckgo_search import DDGS
            
            # Construct city-specific query
            if city.lower() == "ottawa":
                full_query = f"{query} {city} Ontario Canada"
            else:
                full_query = f"{query} {city}"
            
            logger.info(f"🔍 DuckDuckGo search (fallback): {full_query}")
            
            results = []
            
            try:
                with DDGS() as ddgs:
                    search_results = ddgs.text(
                        full_query, 
                        max_results=20,
                        region='ca-en',
                        safesearch='moderate'
                    )
                    
                    for r in search_results:
                        url = r.get('href', '')
                        title = r.get('title', '')
                        snippet = r.get('body', '')
                        
                        if url and self._is_relevant_url_for_content(url, query):
                            results.append({
                                'title': title,
                                'url': url,
                                'snippet': snippet,
                                'source': 'duckduckgo'
                            })
                            
                        if len(results) >= 15:
                            break
                            
            except Exception as search_error:
                logger.warning(f"DuckDuckGo search failed: {search_error}")
            
            logger.info(f"DuckDuckGo found {len(results)} results")
            return results
            
        except ImportError:
            logger.warning("duckduckgo_search not available")
            return self._fallback_web_search(query, city)
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return self._fallback_web_search(query, city)
    
    def _fallback_web_search(self, query: str, city: str) -> List[Dict[str, Any]]:
        """Last resort fallback"""
        logger.info("Using final fallback search method")
        search_query = f"{query} {city}".replace(' ', '+')
        return [
            {
                'title': f"Search: {query} in {city}",
                'url': f"https://www.google.com/search?q={search_query}",
                'snippet': f"Manual search for {query} in {city}",
                'source': 'fallback'
            }
        ]
    
    def _is_relevant_url(self, url: str, query: str) -> bool:
        """Check if URL is relevant for the query"""
        # Filter out social media, maps, reviews aggregators, and irrelevant sites
        excluded_domains = [
            'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
            'yelp.com', 'tripadvisor.com', 'google.com', 'youtube.com',
            'pinterest.com', 'reddit.com', 'zhihu.com', 'baidu.com',
            'answers.microsoft.com', 'adultfriendfinder', 'dating',
            'stackoverflow.com', 'github.com', 'wikipedia.org'
        ]
        
        domain = urlparse(url).netloc.lower()
        url_lower = url.lower()
        
        # Exclude based on domain
        for excluded in excluded_domains:
            if excluded in domain:
                return False
        
        # Exclude non-English or suspicious sites
        if any(indicator in domain for indicator in ['.cn', '.ru', '.br', '/pt-br/', '/zh-', '/ja-']):
            return False
        
        # Exclude forum/Q&A sites
        if any(indicator in url_lower for indicator in ['forum', 'question', 'answer', 'thread', '/q/']):
            return False
        
        # Must be HTTPS for security
        if not url.startswith('https://'):
            return False
        
        # Look for relevant content indicators (broad categories)
        query_lower = query.lower()
        content_indicators = [
            # Food/dining
            'restaurant', 'dining', 'food', 'menu', 'cafe', 'bistro',
            'eatery', 'kitchen', 'grill', 'pizza', 'pasta', 'italian',
            # Outdoor/activities  
            'park', 'trail', 'outdoor', 'recreation', 'activity', 'sports',
            'sledding', 'hiking', 'skiing', 'skating', 'hill', 'mountain',
            # Government/official sites
            'ottawa.ca', '.gov', 'city', 'municipal', 'parks', 'recreation',
            # Local content
            'ottawa', 'ontario', 'canada', 'local', 'community', 'guide'
        ]
        
        # If query is about outdoor activities, be more inclusive
        outdoor_query_indicators = ['sled', 'hik', 'trail', 'hill', 'mountain', 'ski', 'park', 'outdoor']
        is_outdoor_query = any(indicator in query_lower for indicator in outdoor_query_indicators)
        
        # Bonus: URL contains relevant terms
        if any(indicator in url_lower for indicator in content_indicators):
            return True
            
        # For outdoor queries, accept official/government sites even without specific keywords
        if is_outdoor_query:
            official_domains = ['ottawa.ca', '.gov.', 'city.', 'parks', 'recreation']
            if any(domain_part in domain for domain_part in official_domains):
                return True
        
        # Check if domain looks like a business (not too long, has reasonable structure)
        domain_parts = domain.split('.')
        if len(domain_parts) > 4:  # Too many subdomains
            return False
        
        # Prefer actual business websites over content aggregators
        return True
    
    def _extract_venue_name(self, soup: BeautifulSoup) -> str:
        """Extract venue name from page with multiple strategies"""
        # Try Open Graph site name first (usually most accurate)
        og_name = soup.select_one('meta[property="og:site_name"]')
        if og_name:
            name = og_name.get('content', '').strip()
            if name and len(name) < 100 and len(name) > 2:
                return name
        
        # Try structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                items = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
                
                for item in items:
                    if isinstance(item, dict) and 'name' in item:
                        name = item['name']
                        if name and 5 < len(name) < 100:
                            return name
            except:
                pass
        
        # Try multiple selectors in priority order
        selectors = [
            'h1.business-name',
            'h1.venue-name',
            'h1.restaurant-name',
            '[itemprop="name"]',
            '.site-title',
            'h1',
            'title'
        ]
        
        for selector in selectors:
            if selector == 'meta[property="og:site_name"]':
                element = soup.select_one(selector)
                if element:
                    name = element.get('content', '').strip()
                    if name and 2 < len(name) < 100:
                        return name
            else:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    # Validate name length and content
                    if text and 2 < len(text) < 100:
                        # Clean up common suffixes from title tags
                        text = re.sub(r'\s*[|-]\s*.+$', '', text)
                        if 2 < len(text) < 100:
                            return text
        
        return "Unknown Venue"
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract venue description with multiple fallback strategies"""
        # Try meta description first (usually best)
        meta_desc = soup.select_one('meta[name="description"]')
        if meta_desc:
            desc = meta_desc.get('content', '').strip()
            if desc and len(desc) > 50:
                return desc
        
        # Try Open Graph description
        og_desc = soup.select_one('meta[property="og:description"]')
        if og_desc:
            desc = og_desc.get('content', '').strip()
            if desc and len(desc) > 50:
                return desc
        
        # Try structured data (JSON-LD)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'description' in data:
                    desc = data['description']
                    if desc and len(desc) > 50:
                        return desc
                # Handle arrays of structured data
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'description' in item:
                            desc = item['description']
                            if desc and len(desc) > 50:
                                return desc
            except:
                pass
        
        # Try common description selectors
        selectors = [
            '.about-section', '.about-content', '.about', 
            '.description', '.intro', '.overview', '.summary',
            '[itemprop="description"]', '.venue-description',
            '.business-description', 'article p', 'main p'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                # Good description should be substantial but not too long
                if 50 < len(text) < 1000:
                    return text[:500]
        
        # Try to get first substantial paragraph
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if 100 < len(text) < 800:  # Substantial paragraph
                # Avoid navigation, footer, cookie notices
                parent_classes = ' '.join(p.parent.get('class', []))
                if not any(skip in parent_classes.lower() for skip in ['nav', 'footer', 'cookie', 'menu']):
                    return text[:500]
        
        return ""
    
    def _extract_contact_info(self, soup: BeautifulSoup, content: str) -> Dict[str, str]:
        """Extract contact information with improved pattern matching"""
        contact = {}
        
        # Try structured data first
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if 'telephone' in data:
                        contact['phone'] = data['telephone']
                    if 'email' in data:
                        contact['email'] = data['email']
                    if 'address' in data:
                        if isinstance(data['address'], dict):
                            addr_parts = [
                                data['address'].get('streetAddress', ''),
                                data['address'].get('addressLocality', ''),
                                data['address'].get('addressRegion', ''),
                                data['address'].get('postalCode', '')
                            ]
                            contact['address'] = ', '.join(filter(None, addr_parts))
                        else:
                            contact['address'] = str(data['address'])
            except:
                pass
        
        # Phone - try multiple strategies
        if not contact.get('phone'):
            # Try specific selectors first
            phone_selectors = ['[itemprop="telephone"]', '.phone', '.telephone', 'a[href^="tel:"]']
            for selector in phone_selectors:
                element = soup.select_one(selector)
                if element:
                    if element.name == 'a':
                        phone = element.get('href', '').replace('tel:', '').strip()
                    else:
                        phone = element.get_text(strip=True)
                    if phone and len(phone) >= 10:
                        contact['phone'] = phone
                        break
            
            # Fall back to regex patterns
            if not contact.get('phone'):
                for pattern in self.patterns['phone']:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        phone = match.group().replace('tel:', '').strip()
                        # Validate it looks like a phone number
                        digits = re.sub(r'\D', '', phone)
                        if len(digits) >= 10:
                            contact['phone'] = phone
                            break
        
        # Email
        if not contact.get('email'):
            # Try selectors first
            email_selectors = ['[itemprop="email"]', '.email', 'a[href^="mailto:"]']
            for selector in email_selectors:
                element = soup.select_one(selector)
                if element:
                    if element.name == 'a':
                        email = element.get('href', '').replace('mailto:', '').strip()
                    else:
                        email = element.get_text(strip=True)
                    if '@' in email and '.' in email:
                        contact['email'] = email
                        break
            
            # Fall back to regex
            if not contact.get('email'):
                for pattern in self.patterns['email']:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        email = match.group().replace('mailto:', '').strip()
                        # Basic email validation
                        if '@' in email and '.' in email and len(email.split('@')[0]) > 0:
                            contact['email'] = email
                            break
        
        # Address
        if not contact.get('address'):
            address_selectors = [
                '[itemprop="address"]',
                '.address', '.location', '.venue-address',
                '.contact-address', '[itemtype*="PostalAddress"]'
            ]
            
            for selector in address_selectors:
                element = soup.select_one(selector)
                if element:
                    addr_text = element.get_text(strip=True)
                    # Validate it looks like an address
                    if len(addr_text) > 10 and (any(char.isdigit() for char in addr_text) or ',' in addr_text):
                        contact['address'] = addr_text
                        break
            
            # Fall back to regex patterns
            if not contact.get('address'):
                for pattern in self.patterns['address']:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        contact['address'] = match.group().strip()
                        break
        
        return contact
    
    def _extract_hours(self, soup: BeautifulSoup, content: str) -> str:
        """Extract operating hours with improved accuracy"""
        # Try structured data first (most reliable)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                # Handle both single objects and arrays
                items = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
                
                for item in items:
                    if not isinstance(item, dict):
                        continue
                        
                    if 'openingHours' in item:
                        hours = item['openingHours']
                        if isinstance(hours, list):
                            return '\n'.join(hours)
                        return str(hours)
                    
                    if 'openingHoursSpecification' in item:
                        spec = item['openingHoursSpecification']
                        if isinstance(spec, list):
                            hours_list = []
                            for s in spec:
                                if isinstance(s, dict):
                                    day = s.get('dayOfWeek', '')
                                    opens = s.get('opens', '')
                                    closes = s.get('closes', '')
                                    if day and opens and closes:
                                        hours_list.append(f"{day}: {opens}-{closes}")
                            if hours_list:
                                return '\n'.join(hours_list)
            except:
                pass
        
        # Try specific selectors
        selectors = [
            '[itemprop="openingHours"]',
            '.hours', '.opening-hours', '.business-hours',
            '.schedule', '.hours-of-operation', '.operating-hours',
            '.open-hours', '#hours', '.store-hours'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                # Validate it looks like hours (contains time indicators)
                if text and (any(day in text.lower() for day in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']) or 
                           any(time in text.lower() for time in ['am', 'pm', ':'])):
                    return text[:300]
        
        # Try multiple elements that might form hours together
        hours_container = soup.select('.hours-row, .hours-item, .hour-item')
        if hours_container:
            hours_lines = [elem.get_text(strip=True) for elem in hours_container if elem.get_text(strip=True)]
            if hours_lines:
                return '\n'.join(hours_lines[:7])  # Max 7 days
        
        # Fall back to regex patterns
        for pattern in self.patterns['hours']:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                hours_text = match.group().strip()[:300]
                # Validate it's not just a fragment
                if len(hours_text) > 10:
                    return hours_text
        
        return ""
    
    def _extract_pricing(self, soup: BeautifulSoup, content: str) -> Dict[str, Any]:
        """Extract pricing information"""
        pricing = {
            'prices_found': [],
            'price_range': '',
            'menu_items': []
        }
        
        # Find all price mentions
        for pattern in self.patterns['price']:
            matches = re.findall(pattern, content, re.IGNORECASE)
            pricing['prices_found'].extend(matches[:5])  # Limit to 5
        
        # Try to find price range
        price_level_selectors = [
            '.price-range', '[itemprop="priceRange"]',
            '.pricing-level'
        ]
        
        for selector in price_level_selectors:
            element = soup.select_one(selector)
            if element:
                pricing['price_range'] = element.get_text(strip=True)
                break
        
        # Extract menu items if it's a restaurant
        menu_selectors = ['.menu', '.menu-item', '.dish', '.food-item']
        for selector in menu_selectors:
            items = soup.select(selector)
            for item in items[:5]:  # Limit to 5 items
                text = item.get_text(strip=True)
                if text and '$' in text:
                    pricing['menu_items'].append(text[:100])
        
        return pricing
    
    def _extract_events(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract upcoming events"""
        events = []
        
        event_selectors = [
            '.event', '.upcoming-event', '.calendar-event',
            '.show', '.performance', '[itemtype*="Event"]'
        ]
        
        for selector in event_selectors:
            elements = soup.select(selector)
            for element in elements[:5]:  # Limit to 5 events
                event = {
                    'title': '',
                    'date': '',
                    'description': ''
                }
                
                # Try to extract event details
                title_elem = element.select_one('h2, h3, h4, .event-title, .title')
                if title_elem:
                    event['title'] = title_elem.get_text(strip=True)
                
                date_elem = element.select_one('.date, .event-date, time, [datetime]')
                if date_elem:
                    event['date'] = date_elem.get_text(strip=True)
                
                event['description'] = element.get_text(strip=True)[:200]
                
                if event['title'] or event['date']:
                    events.append(event)
        
        return events
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract structured data (JSON-LD, microdata)"""
        structured = {}
        
        # JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    structured['json_ld'] = data
                    break
            except:
                pass
        
        return structured
    
    def _extract_highlights(self, soup: BeautifulSoup, content: str) -> List[str]:
        """Extract key highlights/features"""
        highlights = []
        
        # Look for highlight keywords
        highlight_keywords = [
            'award', 'winner', 'featured', 'specialty', 'signature',
            'famous for', 'known for', 'best', 'top rated', 'popular'
        ]
        
        # Search in text for highlights
        for keyword in highlight_keywords:
            pattern = rf'{keyword}[^.!?]*[.!?]'
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches[:2]:  # Limit to 2 per keyword
                if len(match) < 200:
                    highlights.append(match.strip())
        
        return highlights[:5]  # Return top 5 highlights
    
    async def close(self):
        """Clean up resources"""
        try:
            await self.http_client.aclose()
            logger.debug("Intelligent crawler HTTP client closed")
        except Exception as e:
            logger.error(f"Error closing HTTP client: {e}")


    def _extract_sledding_info(self, soup: BeautifulSoup, content: str) -> Dict[str, Any]:
        """
        Extract sledding-specific information from web pages with date-planning focus
        """
        sledding_info = {
            'hills_mentioned': [],
            'locations': [],
            'safety_info': [],
            'best_for': [],
            'features': [],
            'date_suitability': {
                'romantic_factor': 0,
                'couple_friendly': False,
                'scenic_views': False,
                'instagram_worthy': False
            },
            'logistics': {
                'parking': [],
                'accessibility': [],
                'nearby_amenities': []
            },
            'cost_info': {
                'free': False,
                'paid': False,
                'equipment_rental': False,
                'cost_mentions': []
            },
            'best_times': [],
            'unique_features': []
        }
        
        text_content = content.lower()
        
        # Look for specific sledding hill names and locations
        hill_patterns = [
            r'(\w+(?:\s+\w+)*)\s+(?:hill|park|slope|toboggan)',
            r'(?:at|near|in)\s+([^.,]+(?:park|hill|center|centre))',
            r'(\w+(?:\s+\w+){0,3})\s+(?:sledding|tobogganing)',
        ]
        
        for pattern in hill_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                match = match.strip()
                if len(match) > 2 and len(match) < 50:
                    if match not in sledding_info['hills_mentioned']:
                        sledding_info['hills_mentioned'].append(match)
        
        # Extract location information
        location_keywords = ['ottawa', 'nepean', 'kanata', 'orleans', 'barrhaven', 'gloucester', 'cumberland']
        for keyword in location_keywords:
            if keyword in text_content:
                sledding_info['locations'].append(keyword)
        
        # Look for safety information
        safety_keywords = ['safety', 'supervised', 'helmet', 'adult', 'age', 'children', 'lighting']
        safety_sentences = []
        sentences = re.split(r'[.!?]+', content)
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in safety_keywords):
                cleaned = sentence.strip()
                if len(cleaned) > 10 and len(cleaned) < 200:
                    safety_sentences.append(cleaned)
        sledding_info['safety_info'] = safety_sentences[:3]  # Max 3 safety tips
        
        # Extract features and best-for information
        feature_keywords = ['parking', 'washroom', 'bathroom', 'steep', 'gentle', 'beginner', 'family', 'lighting', 'lit']
        best_for_keywords = ['kids', 'children', 'family', 'beginner', 'advanced', 'thrill']
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for keyword in feature_keywords:
                if keyword in sentence_lower and 'feature' not in sentence_lower:
                    cleaned = sentence.strip()
                    if len(cleaned) > 10 and len(cleaned) < 150:
                        sledding_info['features'].append(cleaned)
                        break
            
            for keyword in best_for_keywords:
                if keyword in sentence_lower:
                    cleaned = sentence.strip()
                    if len(cleaned) > 10 and len(cleaned) < 150:
                        sledding_info['best_for'].append(cleaned)
                        break
        
        # Remove duplicates and limit results
        for key in ['features', 'best_for']:
            sledding_info[key] = list(dict.fromkeys(sledding_info[key]))[:3]
        
        # Enhanced date-planning extraction
        self._extract_date_suitability(content, sledding_info)
        self._extract_logistics_info(content, sledding_info)
        self._extract_cost_info(content, sledding_info)
        self._extract_timing_info(content, sledding_info)
        self._extract_unique_features(content, sledding_info)
        
        return sledding_info

    def _extract_date_suitability(self, content: str, sledding_info: Dict) -> None:
        """Extract information relevant to date planning"""
        content_lower = content.lower()
        
        # Romance factor indicators
        romantic_keywords = ['romantic', 'couples', 'date', 'beautiful', 'scenic', 'stunning', 'breathtaking', 'magical', 'cozy']
        romantic_score = sum(1 for keyword in romantic_keywords if keyword in content_lower)
        sledding_info['date_suitability']['romantic_factor'] = min(romantic_score, 5)
        
        # Couple-friendly indicators
        couple_indicators = ['couple', 'two people', 'together', 'partner', 'date night', 'romantic']
        sledding_info['date_suitability']['couple_friendly'] = any(indicator in content_lower for indicator in couple_indicators)
        
        # Scenic views
        scenic_keywords = ['view', 'scenic', 'overlook', 'vista', 'beautiful', 'picturesque', 'instagram', 'photo']
        sledding_info['date_suitability']['scenic_views'] = any(keyword in content_lower for keyword in scenic_keywords)
        
        # Instagram-worthy features
        photo_keywords = ['photo', 'picture', 'instagram', 'selfie', 'snap', 'camera', 'memorable']
        sledding_info['date_suitability']['instagram_worthy'] = any(keyword in content_lower for keyword in photo_keywords)

    def _extract_logistics_info(self, content: str, sledding_info: Dict) -> None:
        """Extract logistics information for date planning"""
        sentences = re.split(r'[.!?]+', content)
        
        # Parking information
        parking_keywords = ['parking', 'park', 'lot', 'space', 'street parking']
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in parking_keywords):
                cleaned = sentence.strip()
                if len(cleaned) > 10 and len(cleaned) < 150 and 'parking' in cleaned.lower():
                    sledding_info['logistics']['parking'].append(cleaned)
        
        # Accessibility
        accessibility_keywords = ['accessible', 'wheelchair', 'stroller', 'easy access', 'barrier-free', 'paved']
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in accessibility_keywords):
                cleaned = sentence.strip()
                if len(cleaned) > 10 and len(cleaned) < 150:
                    sledding_info['logistics']['accessibility'].append(cleaned)
        
        # Nearby amenities (important for dates)
        amenity_keywords = ['restaurant', 'cafe', 'coffee', 'washroom', 'bathroom', 'food', 'hot chocolate', 'warm up']
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in amenity_keywords):
                cleaned = sentence.strip()
                if len(cleaned) > 10 and len(cleaned) < 150:
                    sledding_info['logistics']['nearby_amenities'].append(cleaned)
        
        # Limit results
        for key in sledding_info['logistics']:
            sledding_info['logistics'][key] = sledding_info['logistics'][key][:3]

    def _extract_cost_info(self, content: str, sledding_info: Dict) -> None:
        """Extract cost information for budget planning"""
        content_lower = content.lower()
        
        # Free indicators
        free_keywords = ['free', 'no cost', 'no charge', 'complimentary', 'at no cost']
        sledding_info['cost_info']['free'] = any(keyword in content_lower for keyword in free_keywords)
        
        # Paid indicators
        paid_keywords = ['fee', 'cost', 'price', 'charge', '$', 'admission', 'ticket']
        sledding_info['cost_info']['paid'] = any(keyword in content_lower for keyword in paid_keywords)
        
        # Equipment rental
        rental_keywords = ['rental', 'rent', 'equipment', 'sled rental', 'toboggan rental', 'gear']
        sledding_info['cost_info']['equipment_rental'] = any(keyword in content_lower for keyword in rental_keywords)
        
        # Cost mentions
        cost_patterns = [
            r'\$\d+(?:\.\d{2})?',  # Dollar amounts
            r'free',
            r'no charge',
            r'admission.*\$?\d*'
        ]
        
        for pattern in cost_patterns:
            matches = re.findall(pattern, content_lower)
            sledding_info['cost_info']['cost_mentions'].extend(matches[:3])

    def _extract_timing_info(self, content: str, sledding_info: Dict) -> None:
        """Extract best timing information for dates"""
        sentences = re.split(r'[.!?]+', content)
        
        timing_keywords = ['best time', 'ideal time', 'perfect time', 'recommended', 'avoid crowds', 'busy', 'quiet', 'peaceful']
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in timing_keywords):
                cleaned = sentence.strip()
                if len(cleaned) > 15 and len(cleaned) < 200:
                    sledding_info['best_times'].append(cleaned)
        
        sledding_info['best_times'] = sledding_info['best_times'][:3]

    def _extract_unique_features(self, content: str, sledding_info: Dict) -> None:
        """Extract unique features that make for memorable dates"""
        sentences = re.split(r'[.!?]+', content)
        
        unique_keywords = ['unique', 'special', 'famous', 'known for', 'highlight', 'standout', 'memorable', 'experience']
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in unique_keywords):
                cleaned = sentence.strip()
                # Filter out JavaScript, HTML, and technical content
                if (20 < len(cleaned) < 200 and 
                    not any(js_indicator in cleaned.lower() for js_indicator in 
                           ['<script', 'javascript', 'function', 'push(', '__tcfapi', '&lt;', '&gt;', 'atatags'])):
                    sledding_info['unique_features'].append(cleaned)
        
        sledding_info['unique_features'] = sledding_info['unique_features'][:3]

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """Extract images for visual appeal and date planning"""
        images = {
            'featured_images': [],
            'gallery_images': [],
            'total_found': 0
        }
        
        # Look for featured images (hero images, main photos)
        featured_selectors = [
            'img[class*="hero"]', 'img[class*="featured"]', 'img[class*="banner"]',
            'meta[property="og:image"]', 'meta[name="twitter:image"]',
            'img[class*="main"]', 'img[id*="main"]'
        ]
        
        for selector in featured_selectors:
            elements = soup.select(selector)
            for element in elements:
                if element.name == 'meta':
                    img_url = element.get('content')
                else:
                    img_url = element.get('src') or element.get('data-src')
                
                if img_url:
                    # Make URL absolute
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        from urllib.parse import urljoin
                        img_url = urljoin(base_url, img_url)
                    
                    if img_url.startswith('http') and img_url not in images['featured_images']:
                        images['featured_images'].append(img_url)
        
        # Look for gallery/content images
        content_images = soup.select('img[src], img[data-src]')
        for img in content_images[:10]:  # Limit to prevent overload
            img_url = img.get('src') or img.get('data-src')
            alt_text = img.get('alt', '').lower()
            
            # Skip small images, icons, logos
            if any(skip in img_url.lower() for skip in ['icon', 'logo', 'avatar', 'thumb']):
                continue
            
            if img_url and img_url.startswith('http'):
                images['gallery_images'].append({
                    'url': img_url,
                    'alt': alt_text,
                    'relevant': any(keyword in alt_text for keyword in ['sledding', 'hill', 'snow', 'winter', 'park'])
                })
        
        images['total_found'] = len(images['featured_images']) + len(images['gallery_images'])
        
        # Limit results
        images['featured_images'] = images['featured_images'][:3]
        images['gallery_images'] = images['gallery_images'][:5]
        
        return images

    def _extract_date_planning_info(self, soup: BeautifulSoup, content: str) -> Dict[str, Any]:
        """Extract general date planning information"""
        date_info = {
            'atmosphere': {
                'romantic': False,
                'family_friendly': False,
                'adventurous': False,
                'peaceful': False
            },
            'crowd_levels': [],
            'weather_considerations': [],
            'recommended_duration': [],
            'accessibility': {
                'difficulty_level': 'unknown',
                'physical_requirements': [],
                'age_restrictions': []
            },
            'memorable_aspects': []
        }
        
        content_lower = content.lower()
        
        # Atmosphere detection
        romantic_indicators = ['romantic', 'intimate', 'cozy', 'beautiful sunset', 'scenic view', 'perfect for couples']
        date_info['atmosphere']['romantic'] = any(indicator in content_lower for indicator in romantic_indicators)
        
        family_indicators = ['family', 'kids', 'children', 'all ages', 'family-friendly']
        date_info['atmosphere']['family_friendly'] = any(indicator in content_lower for indicator in family_indicators)
        
        adventure_indicators = ['adventure', 'thrill', 'exciting', 'adrenaline', 'challenging']
        date_info['atmosphere']['adventurous'] = any(indicator in content_lower for indicator in adventure_indicators)
        
        peaceful_indicators = ['peaceful', 'quiet', 'serene', 'tranquil', 'relaxing']
        date_info['atmosphere']['peaceful'] = any(indicator in content_lower for indicator in peaceful_indicators)
        
        # Extract specific information from sentences
        sentences = re.split(r'[.!?]+', content)
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Crowd level information
            crowd_keywords = ['busy', 'crowded', 'quiet', 'peaceful', 'popular', 'less crowded']
            if any(keyword in sentence_lower for keyword in crowd_keywords):
                cleaned = sentence.strip()
                if 10 < len(cleaned) < 150:
                    date_info['crowd_levels'].append(cleaned)
            
            # Weather considerations
            weather_keywords = ['weather', 'snow', 'ice', 'cold', 'winter', 'temperature', 'conditions']
            if any(keyword in sentence_lower for keyword in weather_keywords):
                cleaned = sentence.strip()
                if 10 < len(cleaned) < 150:
                    date_info['weather_considerations'].append(cleaned)
            
            # Duration recommendations
            duration_keywords = ['hours', 'minutes', 'time', 'duration', 'spend', 'visit']
            if any(keyword in sentence_lower for keyword in duration_keywords):
                cleaned = sentence.strip()
                if 10 < len(cleaned) < 150:
                    date_info['recommended_duration'].append(cleaned)
            
            # Memorable aspects (filter out JavaScript)
            memorable_keywords = ['memorable', 'unforgettable', 'special', 'unique', 'amazing', 'incredible']
            if any(keyword in sentence_lower for keyword in memorable_keywords):
                cleaned = sentence.strip()
                # Filter out JavaScript, HTML, and technical content
                if (15 < len(cleaned) < 200 and 
                    not any(js_indicator in cleaned.lower() for js_indicator in 
                           ['<script', 'javascript', 'function', 'push(', '__tcfapi', '&lt;', '&gt;'])):
                    date_info['memorable_aspects'].append(cleaned)
        
        # Limit results
        for key in ['crowd_levels', 'weather_considerations', 'recommended_duration', 'memorable_aspects']:
            date_info[key] = date_info[key][:3]
        
        return date_info


# Global instance getter
_intelligent_crawler = None

def get_intelligent_crawler(scrapingbee_api_key: Optional[str] = None, serpapi_key: Optional[str] = None) -> IntelligentCrawler:
    """Get or create the intelligent crawler instance"""
    global _intelligent_crawler
    if _intelligent_crawler is None:
        import os
        sb_key = scrapingbee_api_key or os.getenv('SCRAPINGBEE_API_KEY')
        serp_key = serpapi_key or os.getenv('SERPAPI_KEY') or os.getenv('SERPAPI_API_KEY')
        _intelligent_crawler = IntelligentCrawler(sb_key, serp_key)
        if serp_key:
            logger.info("✅ Intelligent crawler initialized with SerpAPI (Google Search)")
        else:
            logger.info("⚠️ Intelligent crawler initialized without SerpAPI - using DuckDuckGo fallback")
    return _intelligent_crawler
