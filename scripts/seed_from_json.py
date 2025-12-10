#!/usr/bin/env python3
"""
Seed database from JSON file
Loads date ideas from JSON and inserts them into PostgreSQL with embeddings
Includes vibe prediction using NLP classifier from the ML project
"""

import os
import sys
import json
import logging
import psycopg2
from datetime import datetime
from sentence_transformers import SentenceTransformer
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
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

class JSONDatabaseSeeder:
    """Seeds database from JSON file"""
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.conn = None
    
    def connect_db(self):
        """Connect to database"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info("✅ Connected to database")
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            raise
    
    def close_db(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def generate_embedding(self, text: str):
        """Generate embedding for text"""
        try:
            embedding = self.embedding_model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def predict_vibe(self, idea: dict) -> str:
        """Predict vibe for a date idea using NLP classifier"""
        if not VIBE_PREDICTOR_AVAILABLE:
            return "casual"  # Default vibe

        try:
            # Combine all text for context
            text = f"{idea.get('title', '')} {idea.get('description', '')} {idea.get('venue_name', '')}"

            # Get keyword-based vibes
            vibes = nlp_classifier.get_keyword_vibes(text)

            if not vibes:
                return "casual"

            return ", ".join(vibes)
        except Exception as e:
            logger.warning(f"Error predicting vibe: {e}")
            return "casual"
    
    def seed_from_json(self, json_file: str):
        """Load and seed from JSON file"""
        try:
            # Load JSON
            with open(json_file, 'r') as f:
                ideas = json.load(f)
            
            logger.info(f"📂 Loaded {len(ideas)} ideas from {json_file}")
            
            self.connect_db()
            cursor = self.conn.cursor()
            
            # Seed locations
            location_map = {}
            for idea in ideas:
                city = idea.get('city', 'Unknown')
                if city not in location_map:
                    cursor.execute(
                        """
                        INSERT INTO location (name, address, city, state, country)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (address) DO UPDATE SET name = EXCLUDED.name
                        RETURNING location_id
                        """,
                        (idea.get('venue_name', city), '', city, '', 'Canada')
                    )
                    location_map[city] = cursor.fetchone()[0]
            
            self.conn.commit()
            logger.info(f"✅ Created {len(location_map)} locations")
            
            # Seed categories
            category_map = {}
            all_categories = set()
            for idea in ideas:
                all_categories.update(idea.get('categories', []))
            
            for category in all_categories:
                cursor.execute(
                    """
                    INSERT INTO event_category (name) 
                    VALUES (%s) 
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name 
                    RETURNING category_id
                    """,
                    (category,)
                )
                category_map[category] = cursor.fetchone()[0]
            
            self.conn.commit()
            logger.info(f"✅ Created {len(category_map)} categories")
            
            # Seed events
            for i, idea in enumerate(ideas):
                try:
                    # Generate embedding
                    embedding_text = f"{idea.get('title', '')} {idea.get('description', '')}"
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
                            idea.get('title', 'Unknown'),
                            idea.get('description', ''),
                            idea.get('price_tier', 1) * 25,
                            location_map.get(idea.get('city', 'Unknown')),
                            datetime.now(),
                            datetime.now(),
                            False,
                            0,
                            idea.get('review_count', 0),
                            idea.get('duration_min', 120),
                            idea.get('indoor', True),
                            idea.get('kid_friendly', True),
                            idea.get('website', ''),
                            idea.get('phone', ''),
                            idea.get('rating', 0),
                            idea.get('review_count', 0),
                            embedding,
                            json.dumps({'source': 'json_import', 'vibe': vibe})
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
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"  Processed {i + 1}/{len(ideas)} ideas...")
                
                except Exception as e:
                    logger.error(f"Error seeding idea '{idea.get('title')}': {e}")
                    continue
            
            self.conn.commit()
            logger.info(f"✅ Seeded {len(ideas)} events successfully!")
            
        except Exception as e:
            logger.error(f"❌ Seeding failed: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            if self.conn:
                cursor.close()
                self.close_db()

def main():
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'sparkdates_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres'),
    }
    
    json_file = sys.argv[1] if len(sys.argv) > 1 else 'data/sample_date_ideas.json'
    
    if not Path(json_file).exists():
        logger.error(f"❌ File not found: {json_file}")
        sys.exit(1)
    
    seeder = JSONDatabaseSeeder(db_config)
    seeder.seed_from_json(json_file)

if __name__ == '__main__':
    main()

