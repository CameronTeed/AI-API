#!/usr/bin/env python3
"""
Database seeding script for SparkDates
Fetches date ideas from Google Places API and seeds the PostgreSQL database
"""

import os
import sys
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import googlemaps
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import vibe predictor from ML service
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / 'ml_service'))
    import nlp_classifier
    VIBE_PREDICTOR_AVAILABLE = True
except ImportError:
    VIBE_PREDICTOR_AVAILABLE = False
    logger.warning("⚠️  NLP classifier not available - vibes will not be predicted")

class DatabaseSeeder:
    """Seeds the SparkDates database with date ideas from Google Places"""
    
    def __init__(self, db_config: Dict[str, str], google_api_key: str):
        """Initialize seeder with database and Google API credentials"""
        self.db_config = db_config
        self.google_maps_client = googlemaps.Client(key=google_api_key)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.conn = None
        
    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info("✅ Connected to database")
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    def close_db(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def fetch_google_places(self, query: str, location: str, radius: int = 25000) -> List[Dict[str, Any]]:
        """Fetch places from Google Places API"""
        try:
            logger.info(f"🔍 Searching Google Places for: {query} in {location}")
            
            # Get location coordinates
            geocode_result = self.google_maps_client.geocode(address=location)
            if not geocode_result:
                logger.error(f"Could not geocode location: {location}")
                return []
            
            lat = geocode_result[0]['geometry']['location']['lat']
            lon = geocode_result[0]['geometry']['location']['lng']
            
            # Search for places
            places_result = self.google_maps_client.places_nearby(
                location=(lat, lon),
                radius=radius,
                keyword=query,
                language='en'
            )
            
            places = places_result.get('results', [])
            logger.info(f"Found {len(places)} places")
            
            return places
        except Exception as e:
            logger.error(f"Error fetching from Google Places: {e}")
            return []
    
    def transform_place_to_date_idea(self, place: Dict[str, Any], city: str) -> Dict[str, Any]:
        """Transform Google Place to date idea format"""
        try:
            place_id = place.get('place_id', '')
            name = place.get('name', 'Unknown')
            
            # Get detailed place info
            place_details = self.google_maps_client.place(place_id)['result']
            
            return {
                'title': name,
                'description': place_details.get('formatted_address', '') + '\n' + 
                              (place_details.get('editorial_summary', {}).get('overview', '') or ''),
                'city': city,
                'lat': place.get('geometry', {}).get('location', {}).get('lat', 0),
                'lon': place.get('geometry', {}).get('location', {}).get('lng', 0),
                'price_tier': len(place.get('price_level', '')) or 1,
                'duration_min': 120,
                'indoor': place_details.get('types', []) and 'indoor' not in str(place_details.get('types', [])).lower(),
                'kid_friendly': True,
                'website': place_details.get('website', ''),
                'phone': place_details.get('formatted_phone_number', ''),
                'rating': place.get('rating', 0),
                'review_count': place.get('user_ratings_total', 0),
                'categories': place.get('types', []),
                'address': place_details.get('formatted_address', ''),
            }
        except Exception as e:
            logger.error(f"Error transforming place {place.get('name')}: {e}")
            return None
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using sentence transformer"""
        try:
            embedding = self.embedding_model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def predict_vibe(self, idea: Dict[str, Any]) -> str:
        """Predict vibe for a date idea using NLP classifier"""
        if not VIBE_PREDICTOR_AVAILABLE:
            return "casual"  # Default vibe

        try:
            # Combine all text for context
            text = f"{idea.get('title', '')} {idea.get('description', '')} {idea.get('address', '')}"

            # Get keyword-based vibes
            vibes = nlp_classifier.get_keyword_vibes(text)

            if not vibes:
                return "casual"

            return ", ".join(vibes)
        except Exception as e:
            logger.warning(f"Error predicting vibe: {e}")
            return "casual"

    def seed_locations(self, ideas: List[Dict[str, Any]]) -> Dict[str, int]:
        """Seed location table and return location_id mapping"""
        cursor = self.conn.cursor()
        location_map = {}
        
        try:
            for idea in ideas:
                city = idea['city']
                address = idea['address']
                
                if city not in location_map:
                    cursor.execute(
                        """
                        INSERT INTO location (name, address, city, state, country)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (address) DO UPDATE SET name = EXCLUDED.name
                        RETURNING location_id
                        """,
                        (address[:100], address, city, '', 'Canada')
                    )
                    location_id = cursor.fetchone()[0]
                    location_map[city] = location_id
                    logger.info(f"Created location: {city} (ID: {location_id})")
            
            self.conn.commit()
            return location_map
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error seeding locations: {e}")
            raise
        finally:
            cursor.close()
    
    def seed_categories(self, ideas: List[Dict[str, Any]]) -> Dict[str, int]:
        """Seed event_category table and return category_id mapping"""
        cursor = self.conn.cursor()
        category_map = {}
        
        try:
            all_categories = set()
            for idea in ideas:
                all_categories.update(idea.get('categories', []))
            
            for category in all_categories:
                cursor.execute(
                    "INSERT INTO event_category (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING category_id",
                    (category,)
                )
                category_id = cursor.fetchone()[0]
                category_map[category] = category_id
            
            self.conn.commit()
            logger.info(f"Created {len(category_map)} categories")
            return category_map
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error seeding categories: {e}")
            raise
        finally:
            cursor.close()
    
    def seed_events(self, ideas: List[Dict[str, Any]], location_map: Dict[str, int], 
                   category_map: Dict[str, int]):
        """Seed event table with date ideas"""
        cursor = self.conn.cursor()
        
        try:
            for idea in ideas:
                # Generate embedding
                embedding_text = f"{idea['title']} {idea['description']}"
                embedding = self.generate_embedding(embedding_text)

                # Predict vibe
                vibe = self.predict_vibe(idea)

                # Insert event
                cursor.execute(
                    """
                    INSERT INTO event
                    (title, description, price, location_id, created_time, modified_time,
                     is_ai_recommended, ai_score, popularity, duration_min, indoor,
                     kid_friendly, website, phone, rating, review_count, embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING event_id
                    """,
                    (
                        idea['title'],
                        idea['description'],
                        idea['price_tier'] * 25,  # Estimate price
                        location_map.get(idea['city']),
                        datetime.now(),
                        datetime.now(),
                        False,
                        0,
                        idea['review_count'],
                        idea['duration_min'],
                        idea['indoor'],
                        idea['kid_friendly'],
                        idea['website'],
                        idea['phone'],
                        idea['rating'],
                        idea['review_count'],
                        embedding,
                        json.dumps({'source': 'google_places', 'vibe': vibe})
                    )
                )
                
                event_id = cursor.fetchone()[0]
                
                # Link categories
                for category in idea.get('categories', []):
                    if category in category_map:
                        cursor.execute(
                            "INSERT INTO event_category_link (event_id, category_id) VALUES (%s, %s)",
                            (event_id, category_map[category])
                        )
            
            self.conn.commit()
            logger.info(f"✅ Seeded {len(ideas)} events")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error seeding events: {e}")
            raise
        finally:
            cursor.close()
    
    def seed_database(self, city: str = "Ottawa", queries: Optional[List[str]] = None):
        """Main seeding function"""
        try:
            self.connect_db()
            
            if queries is None:
                queries = [
                    "restaurants romantic date",
                    "activities outdoor adventure",
                    "museums cultural attractions",
                    "parks scenic views",
                    "entertainment nightlife"
                ]
            
            all_ideas = []
            for query in queries:
                places = self.fetch_google_places(query, city)
                for place in places:
                    idea = self.transform_place_to_date_idea(place, city)
                    if idea:
                        all_ideas.append(idea)
            
            if not all_ideas:
                logger.warning("No ideas found to seed")
                return
            
            logger.info(f"📊 Seeding {len(all_ideas)} date ideas...")
            
            location_map = self.seed_locations(all_ideas)
            category_map = self.seed_categories(all_ideas)
            self.seed_events(all_ideas, location_map, category_map)
            
            logger.info("✅ Database seeding completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Seeding failed: {e}")
            raise
        finally:
            self.close_db()

def main():
    """Main entry point"""
    # Get configuration from environment
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'sparkdates_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres'),
    }
    
    google_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    if not google_api_key:
        logger.error("❌ GOOGLE_MAPS_API_KEY environment variable not set")
        sys.exit(1)
    
    city = sys.argv[1] if len(sys.argv) > 1 else "Ottawa"
    
    seeder = DatabaseSeeder(db_config, google_api_key)
    seeder.seed_database(city)

if __name__ == '__main__':
    main()

