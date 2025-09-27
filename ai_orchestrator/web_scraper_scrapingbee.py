#!/usr/bin/env python3
"""
Web scraping module using ScrapingBee for automatically discovering and extracting date ideas
from various websites like Yelp, TripAdvisor, local event sites, etc.
"""
import os
import sys
import re
import json
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from datetime import datetime
import time
from dataclasses import dataclass

# Web scraping dependencies
try:
    import requests
    from bs4 import BeautifulSoup
    import feedparser  # For RSS feeds
    from scrapingbee import ScrapingBeeClient
    import googlemaps
except ImportError as e:
    print(f"Missing required packages: {e}")
    print("Install with: pip install requests beautifulsoup4 feedparser scrapingbee googlemaps")
    sys.exit(1)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from server.tools.vector_store import get_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ScrapedDateIdea:
    """Data class for scraped date ideas"""
    title: str
    description: str = ""
    url: str = ""
    city: str = ""
    price_tier: int = 2
    rating: float = 0.0
    review_count: int = 0
    categories: List[str] = None
    duration_min: int = 60
    indoor: bool = False
    kid_friendly: bool = False
    website: str = ""
    phone: str = ""
    lat: float = 0.0
    lon: float = 0.0
    source: str = "web_scraping"
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = []
        if not self.website:
            self.website = self.url

class ScrapingBeeWebScraper:
    """Base class for web scraping using ScrapingBee"""
    
    def __init__(self, api_key: str = None, delay: float = 0.5):
        self.api_key = api_key or os.getenv('SCRAPINGBEE_API_KEY')
        if not self.api_key:
            raise ValueError("ScrapingBee API key is required. Set SCRAPINGBEE_API_KEY environment variable.")
        
        self.client = ScrapingBeeClient(api_key=self.api_key)
        self.delay = delay  # Minimal delay since ScrapingBee handles rate limiting
        
    def scrape_url(self, url: str, params: Dict[str, Any] = None) -> Optional[BeautifulSoup]:
        """Scrape a single URL using ScrapingBee and return BeautifulSoup object"""
        try:
            logger.info(f"Scraping with ScrapingBee: {url}")
            
            # Default ScrapingBee parameters
            default_params = {
                'render_js': False,
                'premium_proxy': True,
                'country_code': 'ca',  # Canada for Canadian content
                'return_page_source': True
            }
            
            if params:
                default_params.update(params)
            
            response = self.client.get(url, params=default_params)
            
            if response.status_code == 200:
                # Add small delay to be respectful
                time.sleep(self.delay)
                return BeautifulSoup(response.content, 'html.parser')
            else:
                logger.error(f"ScrapingBee returned status {response.status_code} for {url}")
                return None
        
        except Exception as e:
            logger.error(f"Error scraping {url} with ScrapingBee: {e}")
            return None
    
    def extract_text(self, element, max_length: int = None) -> str:
        """Extract and clean text from an element"""
        if not element:
            return ""
        
        text = element.get_text(strip=True)
        if max_length:
            text = text[:max_length]
        
        return text
    
    def extract_rating(self, text: str) -> float:
        """Extract rating from text (e.g., '4.5 stars', '4.5/5')"""
        if not text:
            return 0.0
        
        # Look for patterns like 4.5, 4.5/5, 4.5 stars
        patterns = [
            r'(\d+\.?\d*)\s*(?:/\s*5)?(?:\s*stars?)?',
            r'(\d+\.?\d*)\s*/\s*5',
            r'rating[:\s]*(\d+\.?\d*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                try:
                    rating = float(match.group(1))
                    return min(rating, 5.0)  # Cap at 5.0
                except ValueError:
                    continue
        
        return 0.0
    
    def extract_price_tier(self, text: str) -> int:
        """Extract price tier from text"""
        if not text:
            return 2
        
        text_lower = text.lower()
        
        # Look for dollar signs
        dollar_count = text.count('$')
        if dollar_count > 0:
            return min(dollar_count, 5)
        
        # Look for price keywords
        if any(word in text_lower for word in ['free', 'budget', 'cheap', 'affordable']):
            return 1
        elif any(word in text_lower for word in ['expensive', 'luxury', 'premium', 'upscale']):
            return 4
        elif any(word in text_lower for word in ['moderate', 'mid-range']):
            return 3
        
        return 2  # Default

class YelpScrapingBeeScraper(ScrapingBeeWebScraper):
    """Scraper for Yelp date ideas using ScrapingBee"""
    
    def scrape_date_ideas(self, city: str = "Ottawa", limit: int = 20) -> List[ScrapedDateIdea]:
        """Scrape date ideas from Yelp"""
        ideas = []
        
        # Search terms for date-appropriate venues
        search_terms = [
            "romantic restaurants",
            "date night activities", 
            "couples activities",
            "fun date spots",
            "entertainment venues"
        ]
        
        for term in search_terms:
            # Use ScrapingBee with JavaScript rendering for Yelp
            url = f"https://www.yelp.com/search?find_desc={term}&find_loc={city}"
            soup = self.scrape_url(url, {'render_js': True, 'wait': 3000})
            
            if not soup:
                continue
            
            # Extract business listings with updated selectors
            businesses = soup.find_all('div', {'data-testid': re.compile(r'serp-ia-card')}) or \
                        soup.find_all('div', class_=re.compile(r'businessName')) or \
                        soup.find_all('div', class_=re.compile(r'result'))
            
            for business in businesses[:limit]:
                try:
                    idea = self.extract_yelp_business(business, city)
                    if idea:
                        ideas.append(idea)
                except Exception as e:
                    logger.error(f"Error extracting Yelp business: {e}")
                    continue
        
        return ideas[:limit]  # Limit total results
    
    def extract_yelp_business(self, business_element, city: str) -> Optional[ScrapedDateIdea]:
        """Extract date idea from Yelp business element"""
        try:
            # Extract title - try multiple selectors
            title_elem = business_element.find('a', class_=re.compile(r'businessName')) or \
                        business_element.find('h3') or \
                        business_element.find('h4') or \
                        business_element.find('a', {'data-testid': 'business-name'})
            
            if not title_elem:
                return None
            
            title = self.extract_text(title_elem)
            if not title:
                return None
            
            # Extract description (categories, snippets)
            description_parts = []
            
            # Categories
            category_elem = business_element.find('span', class_=re.compile(r'category')) or \
                           business_element.find('span', {'data-testid': 'business-categories'})
            if category_elem:
                categories = [cat.strip() for cat in self.extract_text(category_elem).split(',')]
                description_parts.extend(categories)
            
            # Review snippet
            snippet_elem = business_element.find('span', class_=re.compile(r'review')) or \
                          business_element.find('p', class_=re.compile(r'snippet')) or \
                          business_element.find('span', {'data-testid': 'review-snippet'})
            if snippet_elem:
                snippet = self.extract_text(snippet_elem, 200)
                if snippet:
                    description_parts.append(snippet)
            
            description = ". ".join(description_parts) if description_parts else ""
            
            # Extract rating
            rating = 0.0
            rating_elem = business_element.find('div', {'role': 'img'}) or \
                         business_element.find('span', class_=re.compile(r'rating')) or \
                         business_element.find('div', {'data-testid': 'rating'})
            if rating_elem:
                rating_text = rating_elem.get('aria-label', '') or self.extract_text(rating_elem)
                rating = self.extract_rating(rating_text)
            
            # Extract review count
            review_count = 0
            review_elem = business_element.find('span', string=re.compile(r'\d+\s+reviews?')) or \
                         business_element.find('span', {'data-testid': 'review-count'})
            if review_elem:
                match = re.search(r'(\d+)', self.extract_text(review_elem))
                if match:
                    review_count = int(match.group(1))
            
            # Extract price tier
            price_tier = 2
            price_elem = business_element.find('span', string=re.compile(r'\$+')) or \
                        business_element.find('span', {'data-testid': 'price-range'})
            if price_elem:
                price_tier = self.extract_price_tier(self.extract_text(price_elem))
            
            # Extract URL
            url = ""
            link_elem = business_element.find('a', href=True)
            if link_elem:
                url = urljoin("https://www.yelp.com", link_elem['href'])
            
            return ScrapedDateIdea(
                title=title,
                description=description,
                url=url,
                city=city,
                rating=rating,
                review_count=review_count,
                price_tier=price_tier,
                categories=['restaurant', 'date_night'] if 'restaurant' in description.lower() else ['date_night'],
                source="yelp_scrapingbee"
            )
        
        except Exception as e:
            logger.error(f"Error extracting Yelp business: {e}")
            return None

class EventbriteScrapingBeeScraper(ScrapingBeeWebScraper):
    """Scraper for Eventbrite date events using ScrapingBee"""
    
    def scrape_date_ideas(self, city: str = "Ottawa", limit: int = 10) -> List[ScrapedDateIdea]:
        """Scrape date events from Eventbrite"""
        ideas = []
        
        search_terms = [
            "date night",
            "couples workshop",
            "romantic evening",
            "wine tasting",
            "cooking class"
        ]
        
        for term in search_terms:
            url = f"https://www.eventbrite.com/d/{city.lower()}--canada/{term.replace(' ', '-')}/"
            soup = self.scrape_url(url, {'render_js': True, 'wait': 2000})
            
            if not soup:
                continue
            
            # Extract event listings
            events = soup.find_all('div', class_=re.compile(r'discover-search-desktop-card')) or \
                    soup.find_all('article', class_=re.compile(r'event-card')) or \
                    soup.find_all('div', {'data-testid': 'event-card'})
            
            for event in events[:limit]:
                try:
                    idea = self.extract_eventbrite_event(event, city)
                    if idea:
                        ideas.append(idea)
                except Exception as e:
                    logger.error(f"Error extracting Eventbrite event: {e}")
                    continue
        
        return ideas[:limit]
    
    def extract_eventbrite_event(self, event_element, city: str) -> Optional[ScrapedDateIdea]:
        """Extract date idea from Eventbrite event element"""
        try:
            # Extract title
            title_elem = event_element.find('h3') or event_element.find('h2') or \
                        event_element.find('a', class_=re.compile(r'event-card-link')) or \
                        event_element.find('a', {'data-testid': 'event-title'})
            
            if not title_elem:
                return None
            
            title = self.extract_text(title_elem)
            if not title:
                return None
            
            # Extract description
            desc_elem = event_element.find('p') or \
                       event_element.find('div', class_=re.compile(r'description')) or \
                       event_element.find('div', {'data-testid': 'event-summary'})
            description = self.extract_text(desc_elem, 300) if desc_elem else ""
            
            # Extract URL
            url = ""
            link_elem = event_element.find('a', href=True)
            if link_elem:
                href = link_elem['href']
                if href.startswith('http'):
                    url = href
                else:
                    url = urljoin("https://www.eventbrite.com", href)
            
            # Extract price info
            price_tier = 2
            price_elem = event_element.find('span', class_=re.compile(r'price')) or \
                        event_element.find('div', string=re.compile(r'free|Free|\$')) or \
                        event_element.find('span', {'data-testid': 'price'})
            if price_elem:
                price_text = self.extract_text(price_elem).lower()
                if 'free' in price_text:
                    price_tier = 1
                else:
                    price_tier = self.extract_price_tier(price_text)
            
            return ScrapedDateIdea(
                title=title,
                description=description,
                url=url,
                city=city,
                price_tier=price_tier,
                categories=['event', 'date_night'],
                duration_min=120,  # Events are typically longer
                source="eventbrite_scrapingbee"
            )
        
        except Exception as e:
            logger.error(f"Error extracting Eventbrite event: {e}")
            return None

class TripAdvisorScrapingBeeScraper(ScrapingBeeWebScraper):
    """Scraper for TripAdvisor activities using ScrapingBee"""
    
    def scrape_date_ideas(self, city: str = "Ottawa", limit: int = 15) -> List[ScrapedDateIdea]:
        """Scrape date activities from TripAdvisor"""
        ideas = []
        
        # TripAdvisor attractions/activities
        city_formatted = city.replace(' ', '_')
        url = f"https://www.tripadvisor.com/Attractions-g{self.get_city_code(city)}-Activities-{city_formatted}.html"
        
        soup = self.scrape_url(url, {'render_js': True, 'wait': 3000})
        if not soup:
            return ideas
        
        # Extract attraction listings with updated selectors
        attractions = soup.find_all('div', class_=re.compile(r'attraction')) or \
                     soup.find_all('div', {'data-automation': 'cardWrapper'}) or \
                     soup.find_all('div', class_=re.compile(r'listing'))
        
        for attraction in attractions[:limit]:
            try:
                idea = self.extract_tripadvisor_attraction(attraction, city)
                if idea:
                    ideas.append(idea)
            except Exception as e:
                logger.error(f"Error extracting TripAdvisor attraction: {e}")
                continue
        
        return ideas
    
    def get_city_code(self, city: str) -> str:
        """Get TripAdvisor city code (simplified)"""
        city_codes = {
            'ottawa': '155004',
            'toronto': '155019',
            'montreal': '155032',
            'vancouver': '154943',
            'calgary': '154913'
        }
        return city_codes.get(city.lower(), '155004')  # Default to Ottawa
    
    def extract_tripadvisor_attraction(self, attraction_element, city: str) -> Optional[ScrapedDateIdea]:
        """Extract date idea from TripAdvisor attraction element"""
        try:
            # Extract title
            title_elem = attraction_element.find('a') or \
                        attraction_element.find('h3') or \
                        attraction_element.find('div', {'data-automation': 'attraction-title'})
            if not title_elem:
                return None
            
            title = self.extract_text(title_elem)
            if not title:
                return None
            
            # Extract description
            desc_elem = attraction_element.find('p') or \
                       attraction_element.find('div', class_=re.compile(r'description')) or \
                       attraction_element.find('div', {'data-automation': 'attraction-description'})
            description = self.extract_text(desc_elem, 250) if desc_elem else ""
            
            # Extract rating
            rating = 0.0
            rating_elem = attraction_element.find('span', class_=re.compile(r'rating')) or \
                         attraction_element.find('div', {'data-automation': 'rating'}) or \
                         attraction_element.find('div', {'role': 'img'})
            if rating_elem:
                rating_text = rating_elem.get('aria-label', '') or self.extract_text(rating_elem)
                rating = self.extract_rating(rating_text)
            
            # Extract review count
            review_count = 0
            review_elem = attraction_element.find('span', string=re.compile(r'\d+.*reviews?')) or \
                         attraction_element.find('span', {'data-automation': 'review-count'})
            if review_elem:
                match = re.search(r'(\d+)', self.extract_text(review_elem))
                if match:
                    review_count = int(match.group(1))
            
            # Extract URL
            url = ""
            link_elem = attraction_element.find('a', href=True)
            if link_elem:
                url = urljoin("https://www.tripadvisor.com", link_elem['href'])
            
            # Determine if indoor based on title/description
            indoor = any(word in (title + " " + description).lower() 
                        for word in ['museum', 'indoor', 'gallery', 'theater', 'cinema', 'mall'])
            
            return ScrapedDateIdea(
                title=title,
                description=description,
                url=url,
                city=city,
                rating=rating,
                review_count=review_count,
                indoor=indoor,
                categories=['attraction', 'tourism'],
                source="tripadvisor_scrapingbee"
            )
        
        except Exception as e:
            logger.error(f"Error extracting TripAdvisor attraction: {e}")
            return None

class GooglePlacesAPIScraper:
    """Scraper using Google Places API for date venues"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('GOOGLE_PLACES_API_KEY')
        if not self.api_key:
            logger.warning("Google Places API key not found. Skipping Google Places integration.")
            self.client = None
        else:
            self.client = googlemaps.Client(key=self.api_key)
    
    def scrape_date_ideas(self, city: str = "Ottawa", limit: int = 20) -> List[ScrapedDateIdea]:
        """Get date ideas from Google Places API"""
        if not self.client:
            return []
        
        ideas = []
        
        # Search queries for date-appropriate places
        search_queries = [
            f"romantic restaurants in {city}",
            f"date night activities {city}",
            f"entertainment venues {city}",
            f"wine bars {city}",
            f"museums {city}",
            f"art galleries {city}",
            f"theaters {city}",
            f"breweries {city}",
            f"cafes {city}"
        ]
        
        for query in search_queries:
            try:
                logger.info(f"Searching Google Places: {query}")
                
                # Text search for places
                places_result = self.client.places(
                    query=query,
                    location=f"{city}, Canada",
                    radius=25000,  # 25km radius
                    language='en'
                )
                
                for place in places_result.get('results', [])[:limit//len(search_queries)]:
                    idea = self.extract_google_place(place, city)
                    if idea:
                        ideas.append(idea)
                        
            except Exception as e:
                logger.error(f"Error searching Google Places for '{query}': {e}")
                continue
        
        return ideas[:limit]
    
    def extract_google_place(self, place: Dict[str, Any], city: str) -> Optional[ScrapedDateIdea]:
        """Extract date idea from Google Places result"""
        try:
            name = place.get('name', '')
            if not name:
                return None
            
            # Get place details
            place_id = place.get('place_id')
            description_parts = []
            
            # Add types as description
            types = place.get('types', [])
            readable_types = [t.replace('_', ' ').title() for t in types if not t.startswith('establishment')]
            if readable_types:
                description_parts.append(', '.join(readable_types))
            
            # Get detailed info if available
            try:
                details = self.client.place(place_id=place_id, fields=[
                    'formatted_phone_number', 'website', 'opening_hours', 
                    'price_level', 'reviews', 'editorial_summary'
                ])
                
                place_details = details.get('result', {})
                
                # Add editorial summary if available
                if 'editorial_summary' in place_details:
                    description_parts.append(place_details['editorial_summary'].get('overview', ''))
                
                # Get phone and website
                phone = place_details.get('formatted_phone_number', '')
                website = place_details.get('website', '')
                
                # Get price level
                price_level = place_details.get('price_level', 2)
                
            except Exception as e:
                logger.debug(f"Could not get detailed info for {name}: {e}")
                phone = ''
                website = ''
                price_level = 2
            
            description = '. '.join(description_parts) if description_parts else ''
            
            # Extract location
            location = place.get('geometry', {}).get('location', {})
            lat = location.get('lat', 0.0)
            lon = location.get('lng', 0.0)
            
            # Extract rating
            rating = place.get('rating', 0.0)
            user_ratings_total = place.get('user_ratings_total', 0)
            
            # Determine categories based on types
            categories = []
            if any(t in types for t in ['restaurant', 'food', 'meal_takeaway']):
                categories.append('restaurant')
            if any(t in types for t in ['bar', 'night_club', 'liquor_store']):
                categories.append('bar')
            if any(t in types for t in ['museum', 'art_gallery', 'tourist_attraction']):
                categories.append('attraction')
            if any(t in types for t in ['movie_theater', 'amusement_park']):
                categories.append('entertainment')
            
            categories.append('date_night')
            
            # Determine if indoor
            indoor = any(t in types for t in [
                'museum', 'art_gallery', 'movie_theater', 'restaurant', 
                'bar', 'cafe', 'library', 'shopping_mall'
            ])
            
            return ScrapedDateIdea(
                title=name,
                description=description,
                url=website or f"https://maps.google.com/maps/place/?q=place_id:{place_id}",
                city=city,
                rating=rating,
                review_count=user_ratings_total,
                price_tier=min(price_level + 1, 5) if price_level else 2,  # Convert 0-4 to 1-5
                categories=categories,
                lat=lat,
                lon=lon,
                phone=phone,
                website=website,
                indoor=indoor,
                source="google_places"
            )
            
        except Exception as e:
            logger.error(f"Error extracting Google Place: {e}")
            return None

class ScrapingBeeDateIdeaScraper:
    """Main scraper orchestrator using ScrapingBee and APIs"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('SCRAPINGBEE_API_KEY')
        if not self.api_key:
            raise ValueError("ScrapingBee API key is required. Set SCRAPINGBEE_API_KEY environment variable.")
        
        # Initialize all scrapers
        self.scrapers = [
            YelpScrapingBeeScraper(api_key=self.api_key, delay=0.5),
            EventbriteScrapingBeeScraper(api_key=self.api_key, delay=0.3),
            TripAdvisorScrapingBeeScraper(api_key=self.api_key, delay=0.7)
        ]
        
        # Add Google Places API scraper if available
        google_places_scraper = GooglePlacesAPIScraper()
        if google_places_scraper.client:
            self.scrapers.append(google_places_scraper)
            logger.info("✅ Google Places API integration enabled")
        else:
            logger.info("⚠️  Google Places API integration disabled (no API key)")
        
        self.vector_store = get_vector_store()
    
    def scrape_all(self, city: str = "Ottawa", max_per_source: int = 10) -> List[ScrapedDateIdea]:
        """Scrape date ideas from all sources using ScrapingBee and APIs"""
        all_ideas = []
        
        for scraper in self.scrapers:
            try:
                scraper_name = scraper.__class__.__name__
                if 'GooglePlaces' in scraper_name:
                    logger.info(f"Getting ideas from {scraper_name} API...")
                else:
                    logger.info(f"Scraping from {scraper_name} using ScrapingBee...")
                
                ideas = scraper.scrape_date_ideas(city, max_per_source)
                all_ideas.extend(ideas)
                logger.info(f"Found {len(ideas)} ideas from {scraper_name}")
            except Exception as e:
                logger.error(f"Error scraping from {scraper.__class__.__name__}: {e}")
                continue
        
        return all_ideas
    
    def filter_date_appropriate_ideas(self, ideas: List[ScrapedDateIdea]) -> List[ScrapedDateIdea]:
        """Filter out non-date appropriate content"""
        filtered_ideas = []
        
        for idea in ideas:
            title_lower = idea.title.lower()
            description_lower = idea.description.lower()
            
            # Skip business/sales seminars and non-date content
            skip_keywords = [
                'pipeline', 'profit', 'sales', 'retirement', 'seminar', 
                'business', 'investment', 'financial', 'corporate',
                'marketing', 'productivity', 'leadership', 'networking',
                'conference', 'workshop', 'training', 'certification'
            ]
            
            if any(keyword in title_lower for keyword in skip_keywords):
                logger.debug(f"Skipping non-date content: {idea.title}")
                continue
                
            # Keep date-appropriate content
            date_keywords = [
                'date', 'romantic', 'dinner', 'restaurant', 'bar', 'entertainment',
                'museum', 'gallery', 'theater', 'concert', 'festival', 'attraction',
                'tour', 'activity', 'experience', 'wine', 'cooking', 'dance',
                'cafe', 'bistro', 'lounge', 'pub', 'brewery', 'distillery'
            ]
            
            is_date_appropriate = (
                any(keyword in title_lower or keyword in description_lower for keyword in date_keywords) or
                any(cat.lower() in ['restaurant', 'entertainment', 'attraction', 'date_night'] 
                    for cat in idea.categories)
            )
            
            if is_date_appropriate:
                filtered_ideas.append(idea)
        
        logger.info(f"Filtered {len(ideas)} ideas to {len(filtered_ideas)} date-appropriate ideas")
        return filtered_ideas

    def deduplicate_ideas(self, ideas: List[ScrapedDateIdea]) -> List[ScrapedDateIdea]:
        """Remove duplicate ideas based on title similarity"""
        unique_ideas = []
        seen_titles = set()
        
        for idea in ideas:
            # Simple deduplication based on title
            title_lower = idea.title.lower().strip()
            
            # Check for exact matches or very similar titles
            is_duplicate = False
            for seen_title in seen_titles:
                if title_lower == seen_title or \
                   (len(title_lower) > 10 and title_lower in seen_title) or \
                   (len(seen_title) > 10 and seen_title in title_lower):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_ideas.append(idea)
                seen_titles.add(title_lower)
        
        logger.info(f"Deduplicated {len(ideas)} ideas to {len(unique_ideas)} unique ideas")
        return unique_ideas
    
    def save_to_database(self, ideas: List[ScrapedDateIdea]) -> bool:
        """Save scraped ideas to database via vector store"""
        try:
            # Convert to dict format expected by vector store
            date_ideas = []
            for idea in ideas:
                date_idea = {
                    'title': idea.title,
                    'description': idea.description,
                    'categories': idea.categories,
                    'city': idea.city,
                    'lat': idea.lat,
                    'lon': idea.lon,
                    'price_tier': idea.price_tier,
                    'duration_min': idea.duration_min,
                    'indoor': idea.indoor,
                    'kid_friendly': idea.kid_friendly,
                    'website': idea.website,
                    'phone': idea.phone,
                    'rating': idea.rating,
                    'review_count': idea.review_count
                }
                date_ideas.append(date_idea)
            
            # Add to vector store
            success = self.vector_store.add_date_ideas(date_ideas)
            if success:
                logger.info(f"Successfully saved {len(date_ideas)} ideas to database")
            else:
                logger.error("Failed to save ideas to database")
            
            return success
        
        except Exception as e:
            logger.error(f"Error saving ideas to database: {e}")
            return False
    
    def export_to_json(self, ideas: List[ScrapedDateIdea], filename: str = None) -> str:
        """Export scraped ideas to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scraped_date_ideas_scrapingbee_{timestamp}.json"
        
        try:
            ideas_data = []
            for idea in ideas:
                idea_dict = {
                    'title': idea.title,
                    'description': idea.description,
                    'url': idea.url,
                    'city': idea.city,
                    'price_tier': idea.price_tier,
                    'rating': idea.rating,
                    'review_count': idea.review_count,
                    'categories': idea.categories,
                    'duration_min': idea.duration_min,
                    'indoor': idea.indoor,
                    'kid_friendly': idea.kid_friendly,
                    'website': idea.website,
                    'phone': idea.phone,
                    'lat': idea.lat,
                    'lon': idea.lon,
                    'source': idea.source,
                    'scraped_at': datetime.now().isoformat()
                }
                ideas_data.append(idea_dict)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(ideas_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(ideas)} ideas to {filename}")
            return filename
        
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return ""
    
    def get_api_usage(self) -> Dict[str, Any]:
        """Get ScrapingBee API usage information"""
        try:
            # Make a simple request to get usage info from headers
            client = ScrapingBeeClient(api_key=self.api_key)
            response = client.get('https://httpbin.org/get', params={'render_js': False})
            
            usage_info = {
                'status_code': response.status_code,
                'api_credits_used': response.headers.get('Spb-Credits-Used', 'Unknown'),
                'api_credits_remaining': response.headers.get('Spb-Credits-Remaining', 'Unknown'),
                'concurrent_requests': response.headers.get('Spb-Concurrent-Requests', 'Unknown'),
            }
            
            logger.info(f"ScrapingBee API usage: {usage_info}")
            return usage_info
        
        except Exception as e:
            logger.error(f"Error getting ScrapingBee API usage: {e}")
            return {}

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape date ideas using ScrapingBee")
    parser.add_argument('--city', default='Ottawa', help='City to search for date ideas')
    parser.add_argument('--max-per-source', type=int, default=10, help='Maximum ideas per source')
    parser.add_argument('--save-db', action='store_true', help='Force save to database (default: auto-save)')
    parser.add_argument('--no-save-db', action='store_true', help='Skip saving to database')
    parser.add_argument('--export-json', action='store_true', help='Export to JSON file')
    parser.add_argument('--output', help='Output JSON filename')
    parser.add_argument('--api-key', help='ScrapingBee API key (overrides env var)')
    parser.add_argument('--usage-info', action='store_true', help='Show API usage information')
    
    args = parser.parse_args()
    
    try:
        scraper = ScrapingBeeDateIdeaScraper(api_key=args.api_key)
        
        if args.usage_info:
            logger.info("🔍 Getting ScrapingBee API usage information...")
            usage = scraper.get_api_usage()
            return
        
        logger.info(f"🔍 Starting ScrapingBee date idea scraping for {args.city}")
        
        # Scrape from all sources
        all_ideas = scraper.scrape_all(args.city, args.max_per_source)
        
        if not all_ideas:
            logger.warning("No ideas scraped")
            return
        
        # Filter for date-appropriate content
        filtered_ideas = scraper.filter_date_appropriate_ideas(all_ideas)
        
        # Deduplicate
        unique_ideas = scraper.deduplicate_ideas(filtered_ideas)
        
        logger.info(f"📊 Scraped {len(unique_ideas)} unique date ideas")
        
        # Save to database by default (can be disabled with --no-save-db flag)
        if not getattr(args, 'no_save_db', False):
            logger.info("💾 Saving to database...")
            success = scraper.save_to_database(unique_ideas)
            if success:
                logger.info("✅ Successfully saved to database")
            else:
                logger.error("❌ Failed to save to database")
        
        # Also save to database if explicitly requested
        elif args.save_db:
            logger.info("💾 Saving to database...")
            success = scraper.save_to_database(unique_ideas)
            if success:
                logger.info("✅ Successfully saved to database")
            else:
                logger.error("❌ Failed to save to database")
        
        # Export to JSON if requested
        if args.export_json or args.output:
            logger.info("📄 Exporting to JSON...")
            filename = scraper.export_to_json(unique_ideas, args.output)
            if filename:
                logger.info(f"✅ Successfully exported to {filename}")
            else:
                logger.error("❌ Failed to export to JSON")
        
        # Show sample results
        logger.info(f"\n📋 Sample scraped ideas:")
        for i, idea in enumerate(unique_ideas[:5], 1):
            logger.info(f"  {i}. {idea.title} ({idea.source})")
            if idea.description:
                logger.info(f"     {idea.description[:100]}...")
        
        logger.info(f"\n🎉 ScrapingBee scraping completed! Found {len(unique_ideas)} unique date ideas")
        
        # Show API usage
        usage = scraper.get_api_usage()
        if usage:
            logger.info(f"📊 API Credits Used: {usage.get('api_credits_used', 'Unknown')}")
            logger.info(f"📊 API Credits Remaining: {usage.get('api_credits_remaining', 'Unknown')}")
    
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.info("💡 Make sure to set SCRAPINGBEE_API_KEY environment variable or use --api-key")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()