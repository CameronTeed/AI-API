"""
Enhanced Agent Tools for AI Chat System
Provides comprehensive tools for web scraping, Google Services, Maps, and database queries
"""

import os
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import httpx
import googlemaps
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

from .vector_store import get_vector_store
from .web_search import WebSearchClient
from .db_client import get_db_client

logger = logging.getLogger(__name__)

class AgentToolsManager:
    """Central manager for all agent tools with enhanced reasoning capabilities"""
    
    def __init__(self):
        logger.debug("🔧 Initializing AgentToolsManager")
        
        # Initialize Google Services
        self.google_api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        self.google_maps_client = None
        if self.google_api_key:
            try:
                self.google_maps_client = googlemaps.Client(key=self.google_api_key)
                logger.debug("✅ Google Maps client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Maps client: {e}")
        
        # Initialize other services
        self.web_client = WebSearchClient()
        self.vector_store = get_vector_store()
        self.geocoder = Nominatim(user_agent="ai-orchestrator")
        
        # Initialize HTTP client for web scraping
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        # Initialize ScrapingBee if API key available
        self.scrapingbee_api_key = os.getenv('SCRAPINGBEE_API_KEY')
        self.scrapingbee_client = None
        if self.scrapingbee_api_key:
            logger.debug("✅ ScrapingBee API key found")
        else:
            logger.debug("⚠️ ScrapingBee API key not found - using basic scraping")
        
        # Tool cache for performance
        self._tool_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        logger.info("🎯 AgentToolsManager fully initialized")

    def analyze_query_intent(self, query: str, constraints: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze user query to determine intent and optimal tool strategy"""
        query_lower = query.lower()
        intent_analysis = {
            "intent": "general",
            "primary_intent": "general",
            "activity_type": "unknown",
            "location_specific": False,
            "time_sensitive": False,
            "budget_conscious": False,
            "recommended_tools": [],
            "search_strategy": "comprehensive",
            "city": "Ottawa",  # Default city
            "category": "general",
            "timeframe": "general"
        }
        
        # Detect activity types
        if any(word in query_lower for word in ["restaurant", "dining", "food", "eat", "meal"]):
            intent_analysis["intent"] = "dining"
            intent_analysis["primary_intent"] = "dining"
            intent_analysis["activity_type"] = "food"
            intent_analysis["category"] = "food"
            intent_analysis["recommended_tools"] = [
                "google_places_search",     # Find restaurants and venues
                "enhanced_web_search",      # Search for food blogs and reviews  
                "search_date_ideas",        # Check curated dining experiences
                "search_featured_dates",    # Unique dining experiences
                "eventbrite_search"         # Food events and tastings
            ]
        elif any(word in query_lower for word in ["outdoor", "hike", "park", "sledding", "skiing", "beach", "trail", "hill", "mountain", "lake", "river"]):
            intent_analysis["intent"] = "outdoor_activity"
            intent_analysis["primary_intent"] = "outdoor_activity"
            intent_analysis["activity_type"] = "outdoor"
            intent_analysis["category"] = "outdoor"
            intent_analysis["recommended_tools"] = [
                "enhanced_web_search",          # Search blogs and websites for outdoor spots
                "google_places_search",         # Find official venues and parks
                "search_date_ideas",            # Check our database
                "search_featured_dates",        # Find unique outdoor experiences
                "eventbrite_search"             # Look for outdoor events
            ]
        elif any(word in query_lower for word in ["event", "concert", "show", "festival", "performance"]):
            intent_analysis["intent"] = "entertainment"
            intent_analysis["primary_intent"] = "entertainment"
            intent_analysis["activity_type"] = "events"
            intent_analysis["category"] = "entertainment"
            intent_analysis["recommended_tools"] = [
                "eventbrite_search", "enhanced_web_search", "search_featured_dates"
            ]
        elif any(word in query_lower for word in ["museum", "gallery", "art", "culture", "exhibit"]):
            intent_analysis["intent"] = "cultural"
            intent_analysis["primary_intent"] = "cultural"
            intent_analysis["activity_type"] = "culture"
            intent_analysis["category"] = "cultural"
            intent_analysis["recommended_tools"] = [
                "google_places_search", "search_featured_dates", "web_scrape_venue_info"
            ]
        elif any(word in query_lower for word in ["class", "classes", "workshop", "lesson", "course", "learn", "cooking", "pottery", "yoga", "fitness", "dance"]):
            intent_analysis["intent"] = "educational"
            intent_analysis["primary_intent"] = "educational"
            intent_analysis["activity_type"] = "classes"
            intent_analysis["category"] = "educational"
            intent_analysis["recommended_tools"] = [
                "eventbrite_search", "google_places_search", "enhanced_web_search", "search_featured_dates"
            ]
        else:
            # Check if this is a date planning request
            date_planning_words = ["date", "dates", "plan", "ideas", "things to do", "activities", "find", "suggest", "recommend"]
            if any(word in query_lower for word in date_planning_words):
                intent_analysis["intent"] = "date_planning"
                intent_analysis["category"] = "comprehensive"
                intent_analysis["recommended_tools"] = [
                    "enhanced_web_search",      # Search for blog posts and articles about activities
                    "search_date_ideas",        # Check our curated database
                    "google_places_search",     # Find venues and locations
                    "search_featured_dates",    # Find unique experiences
                    "eventbrite_search"         # Look for events and activities
                ]
            else:
                # Default comprehensive search
                intent_analysis["intent"] = "general"
                intent_analysis["category"] = "general"
                intent_analysis["recommended_tools"] = [
                    "enhanced_web_search", "search_date_ideas", "google_places_search", "eventbrite_search"
                ]
        
        # Detect city from query
        cities = {
            "ottawa": "Ottawa", "toronto": "Toronto", "montreal": "Montreal", 
            "vancouver": "Vancouver", "calgary": "Calgary"
        }
        for city_key, city_name in cities.items():
            if city_key in query_lower:
                intent_analysis["city"] = city_name
                intent_analysis["location_specific"] = True
                break
        
        # Detect time sensitivity
        time_words = ["today", "tonight", "tomorrow", "weekend", "now", "soon"]
        if any(word in query_lower for word in time_words):
            intent_analysis["time_sensitive"] = True
            intent_analysis["timeframe"] = "immediate"
            intent_analysis["recommended_tools"].insert(0, "eventbrite_search")
        
        # Detect budget consciousness
        budget_words = ["cheap", "free", "budget", "affordable", "expensive", "luxury"]
        if any(word in query_lower for word in budget_words):
            intent_analysis["budget_conscious"] = True
        
        # Adjust strategy based on constraints
        if constraints:
            if constraints.get("budgetTier", 0) <= 1:
                intent_analysis["budget_conscious"] = True
            if constraints.get("indoor") is True:
                intent_analysis["activity_type"] = "indoor"
                # Remove outdoor-focused tools
                intent_analysis["recommended_tools"] = [
                    tool for tool in intent_analysis["recommended_tools"] 
                    if tool != "enhanced_web_search"
                ]
        
        logger.info(f"🧠 Query intent analysis: {intent_analysis['primary_intent']} ({intent_analysis['activity_type']})")
        return intent_analysis

    async def execute_with_fallbacks(self, primary_tool: str, fallback_tools: List[str], **kwargs) -> Dict[str, Any]:
        """Execute a tool with fallback options if the primary fails"""
        tools_to_try = [primary_tool] + fallback_tools
        last_error = None
        
        for tool_name in tools_to_try:
            try:
                logger.info(f"🔧 Trying tool: {tool_name}")
                tool_method = getattr(self, tool_name, None)
                if tool_method:
                    result = await tool_method(**kwargs)
                    if result.get("success", True) and result.get("items"):
                        logger.info(f"✅ Tool {tool_name} succeeded with {len(result.get('items', []))} results")
                        return result
                    else:
                        logger.warning(f"⚠️ Tool {tool_name} returned no results")
                        last_error = f"No results from {tool_name}"
                else:
                    logger.error(f"❌ Tool {tool_name} not found")
                    last_error = f"Tool {tool_name} not available"
            except Exception as e:
                logger.error(f"❌ Tool {tool_name} failed: {e}")
                last_error = str(e)
        
        # All tools failed
        return {
            "success": False,
            "error": f"All tools failed. Last error: {last_error}",
            "items": []
        }

    async def create_execution_plan(self, query: str, constraints: Optional[Dict] = None, user_location: Optional[Dict] = None) -> Dict[str, Any]:
        """Create an intelligent execution plan based on query analysis"""
        intent = self.analyze_query_intent(query, constraints)
        
        plan = {
            "strategy": intent["search_strategy"],
            "primary_tools": intent["recommended_tools"][:3],  # Top 3 tools
            "secondary_tools": intent["recommended_tools"][3:],  # Additional tools
            "fallback_chains": {},
            "parallel_execution": [],
            "sequential_execution": [],
            "expected_sources": []
        }
        
        # Create fallback chains for critical tools
        if "google_places_search" in plan["primary_tools"]:
            plan["fallback_chains"]["google_places_search"] = ["search_featured_dates", "enhanced_web_search"]
        
        if "search_date_ideas" in plan["primary_tools"]:
            plan["fallback_chains"]["search_date_ideas"] = ["search_featured_dates"]
        
        if "eventbrite_search" in plan["primary_tools"]:
            plan["fallback_chains"]["eventbrite_search"] = ["enhanced_web_search"]
        
        # Determine execution strategy
        if intent["time_sensitive"]:
            # Sequential execution for time-sensitive queries
            plan["sequential_execution"] = plan["primary_tools"]
        else:
            # Parallel execution for comprehensive searches
            plan["parallel_execution"] = plan["primary_tools"]
        
        # Set expected data sources
        plan["expected_sources"] = ["vector_store", "google_places", "web", "eventbrite"]
        
        logger.info(f"📋 Execution plan created: {plan['strategy']} strategy with {len(plan['primary_tools'])} primary tools")
        return plan

    async def execute_plan(self, plan: Dict[str, Any], query: str, constraints: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Execute the planned tool strategy"""
        results = {
            "plan_executed": plan,
            "tool_results": {},
            "aggregated_items": [],
            "sources_used": set(),
            "execution_summary": {}
        }
        
        # Extract common parameters
        city = constraints.get("city", "Ottawa") if constraints else "Ottawa"
        if not city and "ottawa" in query.lower():
            city = "Ottawa"
        
        # Prepare tool arguments
        base_args = {"query": query, "city": city}
        if constraints:
            base_args.update(constraints)
        
        # Execute parallel tools
        if plan["parallel_execution"]:
            logger.info(f"🚀 Executing {len(plan['parallel_execution'])} tools in parallel")
            tasks = []
            
            for tool_name in plan["parallel_execution"]:
                # Get filtered arguments for each specific tool
                tool_args = self._get_filtered_tool_args(tool_name, query, city, constraints)
                
                # Add fallback execution
                fallbacks = plan["fallback_chains"].get(tool_name, [])
                tasks.append(self.execute_with_fallbacks(tool_name, fallbacks, **tool_args))
            
            # Execute all tools in parallel
            parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(parallel_results):
                tool_name = plan["parallel_execution"][i]
                if isinstance(result, Exception):
                    logger.error(f"❌ Tool {tool_name} failed: {result}")
                    results["tool_results"][tool_name] = {"success": False, "error": str(result), "items": []}
                else:
                    results["tool_results"][tool_name] = result
                    if result.get("items"):
                        results["aggregated_items"].extend(result["items"])
                        results["sources_used"].add(result.get("source", tool_name))
        
        # Execute sequential tools
        for tool_name in plan["sequential_execution"]:
            logger.info(f"🔧 Executing sequential tool: {tool_name}")
            
            # Get filtered arguments for each specific tool
            tool_args = self._get_filtered_tool_args(tool_name, query, city, constraints)
            
            fallbacks = plan["fallback_chains"].get(tool_name, [])
            result = await self.execute_with_fallbacks(tool_name, fallbacks, **tool_args)
            
            results["tool_results"][tool_name] = result
            if result.get("items"):
                results["aggregated_items"].extend(result["items"])
                results["sources_used"].add(result.get("source", tool_name))
        
        # Create execution summary
        results["execution_summary"] = {
            "total_tools_executed": len(results["tool_results"]),
            "successful_tools": sum(1 for r in results["tool_results"].values() if r.get("success", True)),
            "total_items_found": len(results["aggregated_items"]),
            "sources_used": list(results["sources_used"]),
            "strategy_used": plan["strategy"]
        }
        
        logger.info(f"✅ Plan execution complete: {results['execution_summary']['successful_tools']}/{results['execution_summary']['total_tools_executed']} tools successful, {results['execution_summary']['total_items_found']} total items")
        
        return results
    
    def _get_filtered_tool_args(self, tool_name: str, query: str, city: str, constraints: Optional[Dict] = None) -> Dict[str, Any]:
        """Get filtered arguments for specific tools to avoid parameter mismatches"""
        base_args = {"query": query}
        
        if tool_name == "search_date_ideas" or tool_name == "search_stored_dates":
            args = {"query": query}
            if city != "Ottawa":  # Only add city if it's not the default
                args["city"] = city
            return args
            
        elif tool_name == "search_featured_dates":
            args = {}
            if city != "Ottawa":
                args["city"] = city
            if constraints and constraints.get("category"):
                args["category"] = constraints["category"]
            else:
                args["category"] = "adventure"  # Default category
            return args
            
        elif tool_name == "google_places_search":
            args = {"query": f"{query} {city}"}
            if city != "Ottawa":
                args["location"] = city
            return args
            
        elif tool_name == "enhanced_web_search":
            args = {"query": query}
            if city != "Ottawa":
                args["city"] = city
            return args
            
        elif tool_name == "eventbrite_search":
            args = {"query": query}
            if city != "Ottawa":
                args["city"] = city
            return args
            
        elif tool_name == "web_scrape_venue_info":
            # This tool needs a URL, not a query
            return {"url": "https://example.com", "venue_name": query}
            
        else:
            # Default case - just return basic args
            return {"query": query}

    async def close(self):
        """Clean up resources"""
        if hasattr(self, 'http_client'):
            await self.http_client.aclose()

    # ===== VECTOR STORE / DATABASE TOOLS =====
    
    async def search_stored_dates(self, **kwargs) -> Dict[str, Any]:
        """Search stored date ideas in vector database"""
        try:
            logger.info(f"🔍 Searching stored dates with args: {kwargs}")
            results = self.vector_store.search(**kwargs)
            
            return {
                "success": True,
                "items": results,
                "source": "stored_database",
                "count": len(results)
            }
        except Exception as e:
            logger.error(f"Error searching stored dates: {e}")
            return {
                "success": False,
                "error": str(e),
                "items": []
            }

    async def search_featured_dates(self, city: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
        """Search for featured/unique dates with special filters"""
        try:
            # Enhanced search for featured content
            search_params = {
                "query": "featured unique special romantic exclusive",
                "top_k": 10
            }
            
            if city:
                search_params["city"] = city
                
            if category:
                search_params["categories"] = [category]
                
            # Note: min_rating not supported by vector store, remove it
            # search_params["min_rating"] = 4.0  # High-rated only
            
            logger.info(f"🌟 Searching featured dates with params: {search_params}")
            results = self.vector_store.search(**search_params)
            
            # Filter for truly unique/featured content
            featured_results = []
            for result in results:
                # Look for indicators of featured content
                title = result.get('title', '').lower()
                description = result.get('description', '').lower()
                
                featured_keywords = ['featured', 'exclusive', 'unique', 'special', 'signature', 'premium']
                if any(keyword in title or keyword in description for keyword in featured_keywords):
                    featured_results.append(result)
            
            return {
                "success": True,
                "items": featured_results,
                "source": "featured_database",
                "count": len(featured_results)
            }
            
        except Exception as e:
            logger.error(f"Error searching featured dates: {e}")
            return {
                "success": False,
                "error": str(e),
                "items": []
            }

    # ===== GOOGLE PLACES TOOLS =====
    
    async def google_places_search(self, query: str, location: Optional[str] = None, radius: int = 25000, **kwargs) -> Dict[str, Any]:
        """Search for places using Google Places API"""
        if not self.google_maps_client:
            return {
                "success": False,
                "error": "Google Places API not configured",
                "items": []
            }
        
        try:
            logger.info(f"🗺️ Google Places search: {query} near {location}")
            
            # For text search, include location in the query for better results
            search_query = query
            if location:
                # Ensure location is included in the search query
                if location.lower() not in query.lower():
                    search_query = f"{query} in {location}"
            
            search_params = {
                "query": search_query,
                "language": "en"
            }
            
            # For text search, we can also try to get coordinates and use location bias
            if location:
                try:
                    # Geocode the location to get coordinates
                    geocode_result = self.google_maps_client.geocode(location)
                    if geocode_result:
                        location_coords = geocode_result[0]['geometry']['location']
                        # Use location bias to prefer results near the specified location
                        search_params["location"] = f"{location_coords['lat']},{location_coords['lng']}"
                        search_params["radius"] = radius
                except Exception as e:
                    logger.warning(f"Could not geocode location {location}: {e}")
            
            logger.debug(f"🔍 Google Places search params: {search_params}")
            
            # Execute search
            result = self.google_maps_client.places(**search_params)
            places = result.get('results', [])
            
            # Process and enhance results
            enhanced_places = []
            for place in places[:10]:  # Limit to top 10
                enhanced_place = await self._enhance_google_place(place)
                if enhanced_place:
                    # Filter by location if specified
                    if location:
                        address = enhanced_place.get('address', '').lower()
                        # Check if the result is actually in the requested location
                        if location.lower() in address:
                            enhanced_places.append(enhanced_place)
                        else:
                            logger.debug(f"Filtered out {enhanced_place.get('title')} - not in {location} (address: {address[:100]}...)")
                    else:
                        enhanced_places.append(enhanced_place)
            
            return {
                "success": True,
                "items": enhanced_places,
                "source": "google_places",
                "count": len(enhanced_places)
            }
            
        except Exception as e:
            logger.error(f"Error in Google Places search: {e}")
            return {
                "success": False,
                "error": str(e),
                "items": []
            }

    async def _enhance_google_place(self, place: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Enhance Google Place result with additional details"""
        try:
            place_id = place.get('place_id')
            if not place_id:
                return None
            
            # Get detailed place information
            try:
                details = self.google_maps_client.place(
                    place_id=place_id,
                    fields=['name', 'formatted_address', 'formatted_phone_number', 
                           'website', 'rating', 'user_ratings_total', 'price_level',
                           'opening_hours', 'geometry', 'type', 'photo']
                )
                place_details = details.get('result', {})
            except Exception as e:
                logger.warning(f"Could not get place details for {place_id}: {e}")
                place_details = place
            
            # Extract and format information
            enhanced = {
                "title": place_details.get('name', ''),
                "address": place_details.get('formatted_address', ''),
                "phone": place_details.get('formatted_phone_number', ''),
                "website": place_details.get('website', ''),
                "rating": place_details.get('rating', 0),
                "review_count": place_details.get('user_ratings_total', 0),
                "price_level": place_details.get('price_level', 0),
                "types": place_details.get('type', []),  # Changed from 'types' to 'type'
                "place_id": place_id,
                "source": "google_places"
            }
            
            # Add location data
            geometry = place_details.get('geometry', {})
            location = geometry.get('location', {})
            if location:
                enhanced["lat"] = location.get('lat')
                enhanced["lon"] = location.get('lng')
            
            # Format opening hours
            opening_hours = place_details.get('opening_hours', {})
            if opening_hours:
                enhanced["opening_hours"] = opening_hours.get('weekday_text', [])
                enhanced["open_now"] = opening_hours.get('open_now', False)
            
            # Add photo URLs if available
            photos = place_details.get('photo', [])  # Changed from 'photos' to 'photo'
            if photos:
                # Handle both single photo and list of photos
                if isinstance(photos, list):
                    photo_refs = [photo.get('photo_reference') for photo in photos[:3] if isinstance(photo, dict)]
                elif isinstance(photos, dict):
                    photo_refs = [photos.get('photo_reference')] if photos.get('photo_reference') else []
                else:
                    photo_refs = []
                enhanced["photo_references"] = photo_refs
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Error enhancing Google place: {e}")
            return None

    # ===== WEB SCRAPING TOOLS =====
    
    async def web_scrape_venue_info(self, url: str, venue_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape detailed information about a venue from its website
        Uses intelligent crawler for better extraction
        """
        try:
            logger.info(f"🌐 Intelligent web scraping venue info from: {url}")
            
            # Use the intelligent crawler for better results
            from .intelligent_crawler import get_intelligent_crawler
            crawler = get_intelligent_crawler(self.scrapingbee_api_key)
            
            result = await crawler.extract_venue_information(
                url=url,
                venue_name=venue_name,
                focus_areas=['description', 'contact', 'hours', 'pricing', 'events']
            )
            
            if result.get('success'):
                data = result.get('data', {})
                
                # Format for consistent output
                formatted = {
                    "url": url,
                    "title": data.get('venue_name', venue_name or 'Unknown'),
                    "description": data.get('description', ''),
                    "phone": data.get('contact', {}).get('phone', ''),
                    "email": data.get('contact', {}).get('email', ''),
                    "address": data.get('contact', {}).get('address', ''),
                    "hours": data.get('hours', ''),
                    "pricing": data.get('pricing', {}),
                    "events": data.get('events', []),
                    "highlights": data.get('highlights', []),
                    "structured_data": data.get('structured_data', {}),
                    "source": "intelligent_crawler"
                }
                
                return {
                    "success": True,
                    "data": formatted
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error in intelligent web scraping from {url}: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    def _extract_title(self, soup, fallback_name=None):
        """Extract title from webpage"""
        title_selectors = ['h1', 'title', '.venue-name', '.business-name']
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)
        return fallback_name or "Unknown Venue"

    def _extract_description(self, soup):
        """Extract description from webpage"""
        desc_selectors = [
            '.description', '.about', '.venue-description', 
            'meta[name="description"]', '.intro-text'
        ]
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    return element.get('content', '')
                else:
                    text = element.get_text(strip=True)
                    if len(text) > 50:  # Reasonable description length
                        return text[:500]  # Limit length
        return ""

    def _extract_contact_info(self, soup):
        """Extract contact information"""
        contact = {}
        
        # Phone patterns
        phone_patterns = [
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        ]
        
        text = soup.get_text()
        import re
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                contact['phone'] = match.group()
                break
        
        # Email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            contact['email'] = email_match.group()
        
        return contact

    def _extract_hours(self, soup):
        """Extract operating hours"""
        hours_selectors = ['.hours', '.opening-hours', '.business-hours', '.schedule']
        for selector in hours_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return ""

    def _extract_menu_prices(self, soup):
        """Extract menu or pricing information"""
        price_selectors = ['.menu', '.prices', '.pricing', '.cost']
        for selector in price_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if '$' in text:  # Has pricing info
                    return text[:300]  # Limit length
        return ""

    def _extract_events(self, soup):
        """Extract upcoming events"""
        event_selectors = ['.events', '.upcoming', '.calendar', '.shows']
        events = []
        for selector in event_selectors:
            elements = soup.select(selector)
            for element in elements:
                event_text = element.get_text(strip=True)
                if len(event_text) > 20:  # Reasonable event description
                    events.append(event_text[:200])
        return events

    # ===== MAPS AND GEOLOCATION TOOLS =====
    
    async def get_directions(self, origin: str, destination: str, mode: str = "driving") -> Dict[str, Any]:
        """Get directions between two locations"""
        if not self.google_maps_client:
            return {
                "success": False,
                "error": "Google Maps API not configured"
            }
        
        try:
            logger.info(f"🗺️ Getting directions from {origin} to {destination} via {mode}")
            
            directions = self.google_maps_client.directions(
                origin=origin,
                destination=destination,
                mode=mode,
                units="metric"
            )
            
            if not directions:
                return {
                    "success": False,
                    "error": "No directions found"
                }
            
            route = directions[0]
            leg = route['legs'][0]
            
            return {
                "success": True,
                "data": {
                    "distance": leg['distance']['text'],
                    "duration": leg['duration']['text'],
                    "start_address": leg['start_address'],
                    "end_address": leg['end_address'],
                    "steps": len(route['legs'][0]['steps']),
                    "overview_polyline": route['overview_polyline']['points']
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting directions: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def geocode_location(self, address: str) -> Dict[str, Any]:
        """Convert address to coordinates"""
        try:
            logger.info(f"📍 Geocoding address: {address}")
            
            location = self.geocoder.geocode(address)
            if not location:
                return {
                    "success": False,
                    "error": "Address not found"
                }
            
            return {
                "success": True,
                "data": {
                    "address": location.address,
                    "latitude": location.latitude,
                    "longitude": location.longitude
                }
            }
            
        except Exception as e:
            logger.error(f"Error geocoding address: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def find_nearby_venues(self, lat: float, lon: float, venue_type: str = "restaurant", radius_km: float = 5.0) -> Dict[str, Any]:
        """Find venues near a location using Google Places"""
        if not self.google_maps_client:
            return {
                "success": False,
                "error": "Google Maps API not configured"
            }
        
        try:
            logger.info(f"🔍 Finding {venue_type} venues near {lat}, {lon} within {radius_km}km")
            
            # Use Google Places Nearby Search
            venues = self.google_maps_client.places_nearby(
                location=(lat, lon),
                radius=int(radius_km * 1000),  # Convert to meters
                type=venue_type,
                language='en'
            )
            
            results = []
            for place in venues.get('results', [])[:10]:
                enhanced_place = await self._enhance_google_place(place)
                if enhanced_place:
                    # Calculate distance
                    place_lat = enhanced_place.get('lat')
                    place_lon = enhanced_place.get('lon')
                    if place_lat and place_lon:
                        distance = geodesic((lat, lon), (place_lat, place_lon)).kilometers
                        enhanced_place['distance_km'] = round(distance, 2)
                    
                    results.append(enhanced_place)
            
            return {
                "success": True,
                "items": results,
                "source": "google_nearby",
                "count": len(results)
            }
            
        except Exception as e:
            logger.error(f"Error finding nearby venues: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # ===== GENERAL WEB SEARCH TOOLS =====
    
    async def enhanced_web_search(self, query: str, city: Optional[str] = None, result_type: str = "general") -> Dict[str, Any]:
        """
        Enhanced web search with automatic intelligent crawling
        Searches the web and extracts detailed information from results
        """
        try:
            logger.info(f"🔍 Enhanced web search with crawling: '{query}' in {city or 'general'}, type: {result_type}")
            
            # Use intelligent crawler to search and extract
            from .intelligent_crawler import get_intelligent_crawler
            crawler = get_intelligent_crawler(self.scrapingbee_api_key)
            
            # Determine focus areas based on result type
            focus_areas = []
            if result_type == "events":
                focus_areas = ['events', 'description', 'pricing']
            elif result_type == "reviews":
                focus_areas = ['description', 'highlights']
            elif result_type == "hours":
                focus_areas = ['hours', 'contact']
            elif result_type == "deals":
                focus_areas = ['pricing', 'events', 'highlights']
            else:
                focus_areas = ['description', 'contact', 'hours', 'pricing', 'events']
            
            # Perform intelligent search with automatic extraction
            result = await crawler.intelligent_search_and_extract(
                query=query,
                city=city or "Ottawa",
                max_results=3,  # Process top 3 results
                focus_areas=focus_areas
            )
            
            if result.get('success'):
                venues = result.get('venues', [])
                
                # Format for consistent output
                items = []
                for venue in venues:
                    contact_info = venue.get('contact', {})
                    pricing_info = venue.get('pricing', {})
                    
                    item = {
                        'title': venue.get('venue_name', venue.get('search_title', '')),
                        'url': venue.get('url', ''),
                        'snippet': venue.get('search_snippet', ''),
                        'description': venue.get('description', ''),
                        'phone': contact_info.get('phone', ''),
                        'email': contact_info.get('email', ''),
                        'address': contact_info.get('address', ''),
                        'hours': venue.get('hours', ''),
                        'pricing_info': pricing_info,
                        'price_mentions': pricing_info.get('prices_found', []),
                        'events': venue.get('events', []),
                        'highlights': venue.get('highlights', []),
                        'source': 'enhanced_web_search_crawl'
                    }
                    items.append(item)
                
                return {
                    "success": True,
                    "query": query,
                    "result_type": result_type,
                    "items": items,
                    "count": len(items)
                }
            else:
                # Fallback to basic web client if intelligent search fails
                logger.warning("Intelligent search failed, falling back to basic web search")
                return await self.web_client.search(query=f"{query} {city or ''}", city=city)
                
        except Exception as e:
            logger.error(f"Enhanced web search error: {e}")
            # Fallback to basic web search
            try:
                return await self.web_client.search(query=f"{query} {city or ''}", city=city)
            except:
                return {
                    "success": False,
                    "error": str(e),
                    "items": []
                }

    async def _scrape_page_content(self, url: str) -> Dict[str, Any]:
        """Scrape detailed content from a web page"""
        try:
            logger.info(f"🕷️ Scraping page content from: {url}")
            
            # Use ScrapingBee if available
            if self.scrapingbee_api_key:
                scraped_data = await self.scrapingbee_scrape(url)
                if scraped_data.get('success'):
                    return scraped_data
            
            # Fallback to basic scraping
            response = await self.http_client.get(url, timeout=10.0)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract comprehensive information
            content = {
                "success": True,
                "description": self._extract_comprehensive_description(soup),
                "contact_info": self._extract_contact_info(soup),
                "hours": self._extract_hours(soup),
                "pricing_info": self._extract_pricing_info(soup),
                "events": self._extract_events(soup),
                "address": self._extract_address(soup),
                "classes_info": self._extract_classes_info(soup)  # For educational content
            }
            
            return content
            
        except Exception as e:
            logger.warning(f"Error scraping page content from {url}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_comprehensive_description(self, soup):
        """Extract a comprehensive description from various page elements"""
        descriptions = []
        
        # Try various description sources
        desc_selectors = [
            'meta[name="description"]',
            '.description', '.about', '.intro', '.summary',
            '.content p', 'main p', '.main-content p',
            'h2 + p', 'h3 + p'  # Paragraphs after headings
        ]
        
        for selector in desc_selectors:
            elements = soup.select(selector)
            for element in elements:
                if element.name == 'meta':
                    content = element.get('content', '').strip()
                    if len(content) > 50:
                        descriptions.append(content)
                else:
                    text = element.get_text(strip=True)
                    if len(text) > 50 and len(text) < 500:  # Reasonable length
                        descriptions.append(text)
        
        # Return the longest, most informative description
        if descriptions:
            return max(descriptions, key=len)[:800]  # Limit total length
        return ""

    def _extract_address(self, soup):
        """Extract address information"""
        address_selectors = [
            '[itemtype*="address"]', '.address', '.location', 
            '.venue-address', '.contact-address'
        ]
        
        for selector in address_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        # Try to find address in text using patterns
        import re
        text = soup.get_text()
        # Look for address-like patterns
        address_pattern = r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl)\s*,?\s*[A-Za-z\s]+,\s*[A-Z]{2}'
        match = re.search(address_pattern, text)
        if match:
            return match.group()
        
        return ""

    def _extract_pricing_info(self, soup):
        """Extract pricing information"""
        price_selectors = [
            '.price', '.pricing', '.cost', '.fee', '.tuition',
            '.menu-price', '.class-price', '.course-price'
        ]
        
        pricing_info = []
        for selector in price_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if '$' in text and len(text) < 200:
                    pricing_info.append(text)
        
        return '; '.join(pricing_info[:5]) if pricing_info else ""

    def _extract_classes_info(self, soup):
        """Extract information about classes, courses, or workshops"""
        class_info = []
        
        class_selectors = [
            '.class', '.course', '.workshop', '.lesson',
            '.program', '.training', '.session'
        ]
        
        for selector in class_selectors:
            elements = soup.select(selector)
            for element in elements[:3]:  # Limit to first 3
                text = element.get_text(strip=True)
                if len(text) > 20 and len(text) < 300:
                    class_info.append(text)
        
        return class_info

    async def scrapingbee_scrape(self, url: str, premium_proxy: bool = False, country_code: str = "CA") -> Dict[str, Any]:
        """
        Advanced web scraping using ScrapingBee API for JavaScript-heavy sites
        Falls back to intelligent crawler if ScrapingBee is not available
        """
        if not self.scrapingbee_api_key:
            logger.info("ScrapingBee API key not found, using intelligent crawler fallback")
            return await self.web_scrape_venue_info(url)
        
        try:
            logger.info(f"🐝 ScrapingBee scraping: {url}")
            
            # ScrapingBee API parameters
            params = {
                'api_key': self.scrapingbee_api_key,
                'url': url,
                'render_js': 'true',  # Execute JavaScript
                'wait': '2000',  # Wait 2 seconds for JS to load
                'premium_proxy': str(premium_proxy).lower(),
                'country_code': country_code,
                'block_resources': 'false',  # Allow images, CSS, etc.
                'return_page_source': 'true'
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    "https://app.scrapingbee.com/api/v1/",
                    params=params
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ ScrapingBee successful for {url}")
                    
                    # Parse the returned HTML with intelligent crawler
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Use intelligent extraction
                    from .intelligent_crawler import get_intelligent_crawler
                    crawler = get_intelligent_crawler(self.scrapingbee_api_key)
                    
                    # Extract information from the rendered page
                    extracted = {
                        'url': url,
                        'title': crawler._extract_venue_name(soup),
                        'description': crawler._extract_description(soup),
                        'contact': crawler._extract_contact_info(soup, response.text),
                        'hours': crawler._extract_hours(soup, response.text),
                        'pricing': crawler._extract_pricing(soup, response.text),
                        'events': crawler._extract_events(soup),
                        'highlights': crawler._extract_highlights(soup, response.text),
                        'structured_data': crawler._extract_structured_data(soup),
                        'source': 'scrapingbee'
                    }
                    
                    return {
                        "success": True,
                        "data": extracted
                    }
                    
                elif response.status_code == 401:
                    logger.error("ScrapingBee authentication failed - check API key")
                    return await self.web_scrape_venue_info(url)
                    
                elif response.status_code == 403:
                    logger.error(f"ScrapingBee access forbidden for {url}")
                    return await self.web_scrape_venue_info(url)
                    
                else:
                    logger.warning(f"ScrapingBee error {response.status_code}: {response.text[:200]}")
                    return await self.web_scrape_venue_info(url)
                    
        except httpx.TimeoutException:
            logger.error(f"ScrapingBee timeout for {url}, using fallback")
            return await self.web_scrape_venue_info(url)
            
        except Exception as e:
            logger.error(f"ScrapingBee error: {e}, using fallback")
            return await self.web_scrape_venue_info(url)

    async def eventbrite_search(self, query: str, city: Optional[str] = None, date_range: Optional[str] = None) -> Dict[str, Any]:
        """Search for events on Eventbrite with enhanced content extraction"""
        try:
            logger.info(f"🎫 Eventbrite search: {query} in {city}")
            
            # Build search URL
            base_url = "https://www.eventbrite.com/d/"
            location_slug = city.lower().replace(' ', '-').replace(',', '') if city else "ottawa-on"
            search_url = f"{base_url}{location_slug}--events/{query.replace(' ', '-')}/"
            
            events = []
            
            # Use ScrapingBee if available, otherwise basic scraping
            if self.scrapingbee_api_key:
                result = await self.scrapingbee_scrape(search_url)
                
                # Parse Eventbrite specific data
                if result.get('success'):
                    # Try to extract events from scraped content
                    scraped_events = await self._extract_eventbrite_events(result, search_url)
                    events.extend(scraped_events)
            
            # Try basic scraping as fallback or if ScrapingBee failed
            if not events:
                try:
                    scraped_content = await self._scrape_page_content(search_url)
                    if scraped_content.get('success'):
                        events = await self._extract_eventbrite_events(scraped_content, search_url)
                except Exception as e:
                    logger.warning(f"Basic scraping failed for Eventbrite: {e}")
            
            # Fallback to basic entry if no events found
            if not events:
                events = [{
                    "title": f"Eventbrite Search: {query} events in {city or 'Ottawa'}",
                    "description": f"Search results for {query} events. Visit the link to see current listings.",
                    "url": search_url,
                    "source": "eventbrite",
                    "venue": "Various venues",
                    "price": "Various prices",
                    "date": date_range or "Various dates",
                    "event_type": "search_results"
                }]
            
            return {
                "success": True,
                "items": events,
                "source": "eventbrite",
                "count": len(events)
            }
            
        except Exception as e:
            logger.error(f"Eventbrite search error: {e}")
            return {
                "success": False,
                "error": str(e),
                "items": []
            }

    async def _extract_eventbrite_events(self, scraped_data: Dict[str, Any], base_url: str) -> List[Dict[str, Any]]:
        """Extract individual events from Eventbrite page content"""
        events = []
        
        try:
            # If we have extracted event data
            if scraped_data.get('events'):
                for event_text in scraped_data['events'][:5]:  # Limit to 5 events
                    events.append({
                        "title": self._extract_event_title(event_text),
                        "description": event_text[:300] + "..." if len(event_text) > 300 else event_text,
                        "url": base_url,  # Link back to search page
                        "source": "eventbrite",
                        "venue": scraped_data.get('address', 'See event for details'),
                        "price": self._extract_event_price(event_text),
                        "date": self._extract_event_date(event_text),
                        "event_type": "listing"
                    })
            
            # If we have basic scraped info, create at least one comprehensive entry
            if not events and scraped_data.get('success'):
                events.append({
                    "title": scraped_data.get('title', 'Eventbrite Events'),
                    "description": scraped_data.get('description', 'Events and activities available on Eventbrite') or scraped_data.get('full_description', ''),
                    "url": base_url,
                    "source": "eventbrite",
                    "venue": scraped_data.get('address', ''),
                    "price": scraped_data.get('pricing_info', 'See website for pricing'),
                    "contact_info": scraped_data.get('contact_info', {}),
                    "hours": scraped_data.get('hours', ''),
                    "event_type": "comprehensive"
                })
        
        except Exception as e:
            logger.warning(f"Error extracting Eventbrite events: {e}")
        
        return events

    def _extract_event_title(self, event_text: str) -> str:
        """Extract event title from event text"""
        lines = event_text.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) > 10 and len(line) < 100:  # Reasonable title length
                return line
        return event_text[:60] + "..." if len(event_text) > 60 else event_text

    def _extract_event_price(self, event_text: str) -> str:
        """Extract price information from event text"""
        import re
        price_patterns = [r'\$\d+(?:\.\d{2})?', r'free', r'Free', r'FREE']
        for pattern in price_patterns:
            match = re.search(pattern, event_text, re.IGNORECASE)
            if match:
                return match.group()
        return "Check website"

    def _extract_event_date(self, event_text: str) -> str:
        """Extract date information from event text"""
        import re
        # Look for date patterns
        date_patterns = [
            r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*,?\s+\w+\s+\d{1,2}',
            r'\w+\s+\d{1,2},?\s+\d{4}',
            r'\d{1,2}/\d{1,2}/\d{4}'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, event_text)
            if match:
                return match.group()
        return "See event details"
    
    async def select_optimal_tools_for_query(
        self, 
        query: str, 
        constraints: Optional[Dict] = None, 
        user_location: Optional[Dict] = None,
        max_tools: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Select optimal tools for a query using intelligent analysis
        Returns list of tool recommendations with confidence scores
        """
        analysis = self.analyze_query_intent(query)
        recommended_tools = analysis["recommended_tools"]
        
        # Create tool recommendations with confidence scores
        tool_recommendations = []
        
        for i, tool in enumerate(recommended_tools[:max_tools]):
            confidence = 1.0 - (i * 0.1)  # Decrease confidence for later tools
            
            # Adjust confidence based on query match
            if tool == "google_places_search" and "restaurant" in query.lower():
                confidence += 0.2
            elif tool == "eventbrite_search" and any(word in query.lower() for word in ["event", "tonight", "weekend"]):
                confidence += 0.2
            elif tool == "search_date_ideas" and "idea" in query.lower():
                confidence += 0.2
            
            confidence = min(1.0, confidence)  # Cap at 1.0
            
            tool_recommendations.append({
                "tool": tool,
                "confidence": confidence,
                "reason": f"Recommended for {analysis['intent']} queries in {analysis.get('city', 'general')} context"
            })
        
        return tool_recommendations
    
    def search_date_ideas(self, **kwargs):
        """Alias for search_stored_dates for compatibility"""
        return self.search_stored_dates(**kwargs)

    async def web_search(self, query: str, city: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Legacy web search - alias for enhanced_web_search"""
        return await self.enhanced_web_search(query=query, city=city, **kwargs)

# Global instance
_agent_tools = None

def get_agent_tools() -> AgentToolsManager:
    """Get global agent tools instance"""
    global _agent_tools
    if _agent_tools is None:
        _agent_tools = AgentToolsManager()
    return _agent_tools