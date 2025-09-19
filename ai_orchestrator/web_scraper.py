#!/usr/bin/env python3
"""
Web scraping module for automatically discovering and extracting date ideas
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
except ImportError as e:
    print(f"Missing required packages: {e}")
    print("Install with: pip install requests beautifulsoup4 feedparser")
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

class WebScraper:
    """Base class for web scraping date ideas"""
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay  # Delay between requests to be respectful
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def scrape_url(self, url: str) -> Optional[BeautifulSoup]:
        """Scrape a single URL and return BeautifulSoup object"""
        try:
            logger.info(f"Scraping: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Add delay to be respectful
            time.sleep(self.delay)
            
            return BeautifulSoup(response.content, 'html.parser')
        
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
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

class YelpScraper(WebScraper):
    """Scraper for Yelp date ideas"""
    
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
            url = f"https://www.yelp.com/search?find_desc={term}&find_loc={city}"
            soup = self.scrape_url(url)
            
            if not soup:
                continue
            
            # Extract business listings
            businesses = soup.find_all('div', {'data-testid': re.compile(r'serp-ia-card')}) or \
                        soup.find_all('div', class_=re.compile(r'businessName'))
            
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
            # Extract title
            title_elem = business_element.find('a', class_=re.compile(r'businessName')) or \
                        business_element.find('h3') or \
                        business_element.find('h4')
            
            if not title_elem:
                return None
            
            title = self.extract_text(title_elem)
            if not title:
                return None
            
            # Extract description (categories, snippets)
            description_parts = []
            
            # Categories
            category_elem = business_element.find('span', class_=re.compile(r'category'))
            if category_elem:
                categories = [cat.strip() for cat in self.extract_text(category_elem).split(',')]
                description_parts.extend(categories)
            
            # Review snippet
            snippet_elem = business_element.find('span', class_=re.compile(r'review')) or \
                          business_element.find('p', class_=re.compile(r'snippet'))
            if snippet_elem:
                snippet = self.extract_text(snippet_elem, 200)
                if snippet:
                    description_parts.append(snippet)
            
            description = ". ".join(description_parts) if description_parts else ""
            
            # Extract rating
            rating = 0.0
            rating_elem = business_element.find('div', {'role': 'img'}) or \
                         business_element.find('span', class_=re.compile(r'rating'))
            if rating_elem:
                rating_text = rating_elem.get('aria-label', '') or self.extract_text(rating_elem)
                rating = self.extract_rating(rating_text)
            
            # Extract review count
            review_count = 0
            review_elem = business_element.find('span', string=re.compile(r'\d+\s+reviews?'))
            if review_elem:
                match = re.search(r'(\d+)', self.extract_text(review_elem))
                if match:
                    review_count = int(match.group(1))
            
            # Extract price tier
            price_tier = 2
            price_elem = business_element.find('span', string=re.compile(r'\$+'))
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
                source="yelp"
            )
        
        except Exception as e:
            logger.error(f"Error extracting Yelp business: {e}")
            return None

class EventbriteScraper(WebScraper):
    """Scraper for Eventbrite date events"""
    
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
            soup = self.scrape_url(url)
            
            if not soup:
                continue
            
            # Extract event listings
            events = soup.find_all('div', class_=re.compile(r'discover-search-desktop-card')) or \
                    soup.find_all('article', class_=re.compile(r'event-card'))
            
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
                        event_element.find('a', class_=re.compile(r'event-card-link'))
            
            if not title_elem:
                return None
            
            title = self.extract_text(title_elem)
            if not title:
                return None
            
            # Extract description
            desc_elem = event_element.find('p') or event_element.find('div', class_=re.compile(r'description'))
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
                        event_element.find('div', string=re.compile(r'free|Free|\$'))
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
                source="eventbrite"
            )
        
        except Exception as e:
            logger.error(f"Error extracting Eventbrite event: {e}")
            return None

class TripAdvisorScraper(WebScraper):
    """Scraper for TripAdvisor activities"""
    
    def scrape_date_ideas(self, city: str = "Ottawa", limit: int = 15) -> List[ScrapedDateIdea]:
        """Scrape date activities from TripAdvisor"""
        ideas = []
        
        # TripAdvisor attractions/activities
        city_formatted = city.replace(' ', '_')
        url = f"https://www.tripadvisor.com/Attractions-g{self.get_city_code(city)}-Activities-{city_formatted}.html"
        
        soup = self.scrape_url(url)
        if not soup:
            return ideas
        
        # Extract attraction listings
        attractions = soup.find_all('div', class_=re.compile(r'attraction')) or \
                     soup.find_all('div', {'data-automation': 'cardWrapper'})
        
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
            title_elem = attraction_element.find('a') or attraction_element.find('h3')
            if not title_elem:
                return None
            
            title = self.extract_text(title_elem)
            if not title:
                return None
            
            # Extract description
            desc_elem = attraction_element.find('p') or \
                       attraction_element.find('div', class_=re.compile(r'description'))
            description = self.extract_text(desc_elem, 250) if desc_elem else ""
            
            # Extract rating
            rating = 0.0
            rating_elem = attraction_element.find('span', class_=re.compile(r'rating')) or \
                         attraction_element.find('div', {'data-automation': 'rating'})
            if rating_elem:
                rating_text = rating_elem.get('aria-label', '') or self.extract_text(rating_elem)
                rating = self.extract_rating(rating_text)
            
            # Extract review count
            review_count = 0
            review_elem = attraction_element.find('span', string=re.compile(r'\d+.*reviews?'))
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
                source="tripadvisor"
            )
        
        except Exception as e:
            logger.error(f"Error extracting TripAdvisor attraction: {e}")
            return None

class DateIdeaScraper:
    """Main scraper orchestrator"""
    
    def __init__(self):
        self.scrapers = [
            YelpScraper(delay=1.5),
            EventbriteScraper(delay=1.0),
            TripAdvisorScraper(delay=2.0)
        ]
        self.vector_store = get_vector_store()
    
    def scrape_all(self, city: str = "Ottawa", max_per_source: int = 10) -> List[ScrapedDateIdea]:
        """Scrape date ideas from all sources"""
        all_ideas = []
        
        for scraper in self.scrapers:
            try:
                logger.info(f"Scraping from {scraper.__class__.__name__}...")
                ideas = scraper.scrape_date_ideas(city, max_per_source)
                all_ideas.extend(ideas)
                logger.info(f"Found {len(ideas)} ideas from {scraper.__class__.__name__}")
            except Exception as e:
                logger.error(f"Error scraping from {scraper.__class__.__name__}: {e}")
                continue
        
        return all_ideas
    
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
            filename = f"scraped_date_ideas_{timestamp}.json"
        
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

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape date ideas from various websites")
    parser.add_argument('--city', default='Ottawa', help='City to search for date ideas')
    parser.add_argument('--max-per-source', type=int, default=10, help='Maximum ideas per source')
    parser.add_argument('--save-db', action='store_true', help='Save to database')
    parser.add_argument('--export-json', action='store_true', help='Export to JSON file')
    parser.add_argument('--output', help='Output JSON filename')
    
    args = parser.parse_args()
    
    logger.info(f"🔍 Starting date idea scraping for {args.city}")
    
    scraper = DateIdeaScraper()
    
    # Scrape from all sources
    all_ideas = scraper.scrape_all(args.city, args.max_per_source)
    
    if not all_ideas:
        logger.warning("No ideas scraped")
        return
    
    # Deduplicate
    unique_ideas = scraper.deduplicate_ideas(all_ideas)
    
    logger.info(f"📊 Scraped {len(unique_ideas)} unique date ideas")
    
    # Save to database if requested
    if args.save_db:
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
    
    logger.info(f"\n🎉 Scraping completed! Found {len(unique_ideas)} unique date ideas")

if __name__ == "__main__":
    main()