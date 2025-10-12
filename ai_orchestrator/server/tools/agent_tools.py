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
    """Central manager for all agent tools"""
    
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
        
        logger.info("🎯 AgentToolsManager fully initialized")

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
                           'opening_hours', 'geometry', 'types', 'photos']
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
                "types": place_details.get('types', []),
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
            photos = place_details.get('photos', [])
            if photos:
                photo_refs = [photo.get('photo_reference') for photo in photos[:3]]
                enhanced["photo_references"] = photo_refs
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Error enhancing Google place: {e}")
            return None

    # ===== WEB SCRAPING TOOLS =====
    
    async def web_scrape_venue_info(self, url: str, venue_name: Optional[str] = None) -> Dict[str, Any]:
        """Scrape detailed information about a venue from its website"""
        try:
            logger.info(f"🌐 Web scraping venue info from: {url}")
            
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract key information
            info = {
                "url": url,
                "title": self._extract_title(soup, venue_name),
                "description": self._extract_description(soup),
                "contact_info": self._extract_contact_info(soup),
                "hours": self._extract_hours(soup),
                "menu_prices": self._extract_menu_prices(soup),
                "events": self._extract_events(soup),
                "source": "web_scraping"
            }
            
            return {
                "success": True,
                "data": info
            }
            
        except Exception as e:
            logger.error(f"Error scraping venue info from {url}: {e}")
            return {
                "success": False,
                "error": str(e)
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
        """Enhanced web search with different result types"""
        try:
            logger.info(f"🔍 Enhanced web search: {query} ({result_type})")
            
            # Enhance query based on type
            if result_type == "events":
                query = f"{query} events upcoming schedule"
            elif result_type == "reviews":
                query = f"{query} reviews ratings opinions"
            elif result_type == "deals":
                query = f"{query} deals discounts promotions"
            elif result_type == "hours":
                query = f"{query} hours open closed schedule"
            
            if city:
                query = f"{query} {city}"
            
            # Use existing web search client
            results = await self.web_client.web_search(query, city)
            
            return {
                "success": True,
                "items": results.get('items', []),
                "source": "enhanced_web_search",
                "search_type": result_type
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced web search: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def scrapingbee_scrape(self, url: str, premium_proxy: bool = False, country_code: str = "CA") -> Dict[str, Any]:
        """Advanced web scraping using ScrapingBee API for better reliability"""
        if not self.scrapingbee_api_key:
            # Fallback to basic scraping
            return await self.web_scrape_venue_info(url)
        
        try:
            logger.info(f"🐝 ScrapingBee scraping: {url}")
            
            # ScrapingBee API parameters
            params = {
                'api_key': self.scrapingbee_api_key,
                'url': url,
                'render_js': 'true',  # Execute JavaScript
                'premium_proxy': str(premium_proxy).lower(),
                'country_code': country_code,
                'extract_rules': json.dumps({
                    "title": "title",
                    "meta_description": "meta[name='description']@content",
                    "phone": "a[href^='tel:']@href, .phone, .contact-phone",
                    "email": "a[href^='mailto:']@href, .email",
                    "address": ".address, .location, .venue-address",
                    "hours": ".hours, .opening-hours, .business-hours",
                    "events": ".event, .upcoming-events, .calendar-event",
                    "prices": ".price, .cost, .fee, .pricing"
                })
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://app.scrapingbee.com/api/v1/",
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "success": True,
                        "title": data.get('title', ''),
                        "description": data.get('meta_description', ''),
                        "phone": data.get('phone', ''),
                        "email": data.get('email', ''),
                        "address": data.get('address', ''),
                        "hours": data.get('hours', ''),
                        "events": data.get('events', ''),
                        "prices": data.get('prices', ''),
                        "url": url,
                        "source": "scrapingbee"
                    }
                else:
                    logger.warning(f"ScrapingBee error {response.status_code}: {response.text}")
                    # Fallback to basic scraping
                    return await self.web_scrape_venue_info(url)
                    
        except Exception as e:
            logger.error(f"ScrapingBee error: {e}")
            # Fallback to basic scraping
            return await self.web_scrape_venue_info(url)

    async def eventbrite_search(self, query: str, city: Optional[str] = None, date_range: Optional[str] = None) -> Dict[str, Any]:
        """Search for events on Eventbrite"""
        try:
            logger.info(f"🎫 Eventbrite search: {query} in {city}")
            
            # Build search URL
            base_url = "https://www.eventbrite.com/d/"
            location_slug = city.lower().replace(' ', '-').replace(',', '') if city else "ottawa-on"
            search_url = f"{base_url}{location_slug}--events/{query.replace(' ', '-')}/"
            
            # Use ScrapingBee if available, otherwise basic scraping
            if self.scrapingbee_api_key:
                result = await self.scrapingbee_scrape(search_url)
                events = []
                
                # Parse Eventbrite specific data
                if result.get('success'):
                    events.append({
                        "title": result.get('title', f'Eventbrite: {query}'),
                        "description": result.get('description', f'Events for {query}'),
                        "url": search_url,
                        "source": "eventbrite",
                        "venue": result.get('address', ''),
                        "price": result.get('prices', 'Check website'),
                        "date": date_range or "Various dates"
                    })
            else:
                # Basic Eventbrite integration
                events = [{
                    "title": f"Eventbrite: {query} events",
                    "description": f"Find {query} events in {city}",
                    "url": search_url,
                    "source": "eventbrite_basic",
                    "venue": "Various venues",
                    "price": "Various prices"
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

# Global instance
_agent_tools = None

def get_agent_tools() -> AgentToolsManager:
    """Get global agent tools instance"""
    global _agent_tools
    if _agent_tools is None:
        _agent_tools = AgentToolsManager()
    return _agent_tools