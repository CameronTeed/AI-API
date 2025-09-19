"""
PostgreSQL-backed vector store for date ideas using sentence transformers for embeddings
and pgvector for efficient similarity search.
"""
import json
import logging
import os
import pickle
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from datetime import datetime

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import psycopg
    from pgvector.psycopg import register_vector
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

from ..db_config import get_db_config

logger = logging.getLogger(__name__)

class PostgreSQLVectorStore:
    """PostgreSQL-backed vector store for date ideas with semantic search capabilities"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", use_fallback: bool = True):
        self.model_name = model_name
        self.model = None
        self.use_fallback = use_fallback
        self.db_config = get_db_config()
        
        # Fallback file path for backwards compatibility
        self.fallback_file = os.path.join(
            os.path.dirname(__file__), 
            "../../data/date_ideas_vector_store.pkl"
        )
        
        # Initialize the model
        self._load_model()
        
        # Check database connectivity
        self._check_db_connection()
    
    def _load_model(self):
        """Load the sentence transformer model"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.error("sentence-transformers not available. Install with: pip install sentence-transformers")
            return
            
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded sentence transformer model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer model: {e}")
    
    def _check_db_connection(self):
        """Check if PostgreSQL is available and configured"""
        if not POSTGRESQL_AVAILABLE:
            logger.warning("psycopg or pgvector not available. Install with: pip install psycopg[binary] pgvector")
            return False
        
        try:
            with self.db_config.get_connection() as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.execute("SELECT COUNT(*) FROM date_ideas")
                    count = cur.fetchone()[0]
                    logger.info(f"Connected to PostgreSQL. Found {count} date ideas in database.")
                    return True
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed: {e}")
            if self.use_fallback:
                logger.info("Will use fallback file-based storage")
            return False
    
    def _create_embedding_text(self, date_idea: Dict[str, Any]) -> str:
        """Create text representation of date idea for embedding"""
        parts = []
        
        # Title and description are most important
        if date_idea.get("title"):
            parts.append(date_idea["title"])
        if date_idea.get("description"):
            parts.append(date_idea["description"])
        
        # Add categories
        if date_idea.get("categories"):
            if isinstance(date_idea["categories"], list):
                categories_text = " ".join(date_idea["categories"])
            else:
                categories_text = str(date_idea["categories"])
            parts.append(f"Categories: {categories_text}")
        
        # Add location info
        if date_idea.get("city"):
            parts.append(f"City: {date_idea['city']}")
        
        # Add address if available
        if date_idea.get("address"):
            parts.append(f"Address: {date_idea['address']}")
        
        # Add neighborhood if available
        if date_idea.get("neighborhood"):
            parts.append(f"Neighborhood: {date_idea['neighborhood']}")
        
        # Add price tier info
        price_map = {1: "budget-friendly", 2: "moderate", 3: "expensive"}
        if date_idea.get("price_tier"):
            price_desc = price_map.get(date_idea["price_tier"], "")
            if price_desc:
                parts.append(f"Price: {price_desc}")
        
        # Add duration info
        if date_idea.get("duration_min"):
            duration = date_idea["duration_min"]
            if duration < 60:
                parts.append(f"Duration: {duration} minutes")
            else:
                hours = duration // 60
                parts.append(f"Duration: {hours} hours")
        
        # Add indoor/outdoor info
        if "indoor" in date_idea:
            if date_idea["indoor"]:
                parts.append("indoor activity")
            else:
                parts.append("outdoor activity")
        
        return " ".join(parts)
    
    def add_date_ideas(self, date_ideas: List[Dict[str, Any]]) -> bool:
        """Add date ideas to the vector store"""
        if not self.model:
            logger.error("Model not loaded - cannot add date ideas")
            return False
        
        logger.info(f"Adding {len(date_ideas)} date ideas to vector store")
        
        # Create embeddings
        embedding_texts = [self._create_embedding_text(idea) for idea in date_ideas]
        
        try:
            embeddings = self.model.encode(embedding_texts, convert_to_numpy=True)
            logger.info(f"Created embeddings with shape: {embeddings.shape}")
        except Exception as e:
            logger.error(f"Failed to create embeddings: {e}")
            return False
        
        # Try to save to PostgreSQL first
        if POSTGRESQL_AVAILABLE and self._save_to_postgresql(date_ideas, embeddings):
            logger.info("Successfully saved to PostgreSQL")
            return True
        elif self.use_fallback:
            logger.info("Falling back to file-based storage")
            return self._save_to_file(date_ideas, embeddings)
        else:
            logger.error("Failed to save date ideas - no storage backend available")
            return False
    
    def _save_to_postgresql(self, date_ideas: List[Dict[str, Any]], embeddings: np.ndarray) -> bool:
        """Save date ideas and embeddings to PostgreSQL using Java schema"""
        try:
            with self.db_config.get_connection() as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    # Insert/update events and related data
                    for i, idea in enumerate(date_ideas):
                        embedding_vector = embeddings[i].tolist()
                        
                        # Handle location first
                        location_id = self._upsert_location(cur, idea)
                        
                        # Handle categories
                        category_ids = self._upsert_categories(cur, idea.get("categories", []))
                        
                        # Handle event
                        event_id = self._upsert_event(cur, idea, location_id, embedding_vector)
                        
                        # Link categories to event
                        self._link_event_categories(cur, event_id, category_ids)
                    
                    conn.commit()
                    logger.info(f"Saved {len(date_ideas)} date ideas to PostgreSQL (Java schema)")
                    return True
        except Exception as e:
            logger.error(f"Failed to save to PostgreSQL: {e}")
            return False
    
    def _upsert_location(self, cur, idea: Dict[str, Any]) -> Optional[int]:
        """Insert or update location and return location_id"""
        city = idea.get("city", "")
        address = idea.get("address", "")
        venue_name = idea.get("venue_name", "")
        lat = idea.get("lat", 0.0)
        lon = idea.get("lon", 0.0)
        
        if not city and not address and not venue_name:
            return None
        
        # Try to find existing location
        cur.execute("""
            SELECT location_id FROM location 
            WHERE city = %s AND COALESCE(address, '') = %s AND COALESCE(name, '') = %s
        """, (city, address, venue_name))
        
        result = cur.fetchone()
        if result:
            location_id = result[0]
            # Update coordinates if provided
            if lat != 0.0 or lon != 0.0:
                cur.execute("""
                    UPDATE location SET lat = %s, lon = %s 
                    WHERE location_id = %s AND (lat IS NULL OR lon IS NULL)
                """, (lat, lon, location_id))
            return location_id
        
        # Insert new location
        cur.execute("""
            INSERT INTO location (name, address, city, lat, lon)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING location_id
        """, (venue_name, address, city, lat, lon))
        
        return cur.fetchone()[0]
    
    def _upsert_categories(self, cur, categories: List[str]) -> List[int]:
        """Insert or update categories and return category_ids"""
        category_ids = []
        
        for category in categories:
            if not category:
                continue
                
            # Try to find existing category
            cur.execute("SELECT category_id FROM event_category WHERE name = %s", (category,))
            result = cur.fetchone()
            
            if result:
                category_ids.append(result[0])
            else:
                # Insert new category
                cur.execute("""
                    INSERT INTO event_category (name) VALUES (%s)
                    RETURNING category_id
                """, (category,))
                category_ids.append(cur.fetchone()[0])
        
        return category_ids
    
    def _upsert_event(self, cur, idea: Dict[str, Any], location_id: Optional[int], embedding_vector: List[float]) -> int:
        """Insert or update event and return event_id"""
        # Extract event ID from the idea ID if it exists
        idea_id = idea.get("id", "")
        event_id = None
        
        if idea_id.startswith("event_"):
            try:
                event_id = int(idea_id.replace("event_", ""))
            except ValueError:
                event_id = None
        
        # Calculate price from price_tier if price not provided
        price = idea.get("price")
        if price is None:
            price_tier = idea.get("price_tier", 1)
            price_map = {1: 25.0, 2: 75.0, 3: 150.0}
            price = price_map.get(price_tier, 25.0)
        
        # Prepare event data
        event_data = {
            "title": idea.get("title", "Untitled Event"),
            "description": idea.get("description", ""),
            "price": price,
            "location_id": location_id,
            "duration_min": idea.get("duration_min", 60),
            "indoor": idea.get("indoor", False),
            "kid_friendly": idea.get("kid_friendly", False),
            "website": idea.get("website", ""),
            "phone": idea.get("phone", ""),
            "rating": idea.get("rating", 0.0),
            "review_count": idea.get("review_count", 0),
            "is_ai_recommended": True,  # Mark as AI recommended since it's from vector store
            "ai_score": idea.get("similarity_score", 0.0) if "similarity_score" in idea else 5.0,
            "popularity": idea.get("popularity", 0),
            "embedding": embedding_vector,
            "metadata": json.dumps(idea.get("metadata", {}))
        }
        
        if event_id:
            # Update existing event
            cur.execute("""
                UPDATE event SET
                    title = %s, description = %s, price = %s, location_id = %s,
                    duration_min = %s, indoor = %s, kid_friendly = %s,
                    website = %s, phone = %s, rating = %s, review_count = %s,
                    is_ai_recommended = %s, ai_score = %s, popularity = %s,
                    embedding = %s, metadata = %s, modified_time = NOW()
                WHERE event_id = %s
                RETURNING event_id
            """, (
                event_data["title"], event_data["description"], event_data["price"], event_data["location_id"],
                event_data["duration_min"], event_data["indoor"], event_data["kid_friendly"],
                event_data["website"], event_data["phone"], event_data["rating"], event_data["review_count"],
                event_data["is_ai_recommended"], event_data["ai_score"], event_data["popularity"],
                event_data["embedding"], event_data["metadata"], event_id
            ))
            result = cur.fetchone()
            return result[0] if result else event_id
        else:
            # Insert new event
            cur.execute("""
                INSERT INTO event (
                    title, description, price, location_id, duration_min, indoor, kid_friendly,
                    website, phone, rating, review_count, is_ai_recommended, ai_score, popularity,
                    embedding, metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING event_id
            """, (
                event_data["title"], event_data["description"], event_data["price"], event_data["location_id"],
                event_data["duration_min"], event_data["indoor"], event_data["kid_friendly"],
                event_data["website"], event_data["phone"], event_data["rating"], event_data["review_count"],
                event_data["is_ai_recommended"], event_data["ai_score"], event_data["popularity"],
                event_data["embedding"], event_data["metadata"]
            ))
            return cur.fetchone()[0]
    
    def _link_event_categories(self, cur, event_id: int, category_ids: List[int]):
        """Link event to categories"""
        if not category_ids:
            return
        
        # Clear existing links
        cur.execute("DELETE FROM event_category_link WHERE event_id = %s", (event_id,))
        
        # Insert new links
        for category_id in category_ids:
            cur.execute("""
                INSERT INTO event_category_link (event_id, category_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (event_id, category_id))
    
    def _save_to_file(self, date_ideas: List[Dict[str, Any]], embeddings: np.ndarray) -> bool:
        """Fallback: save to pickle file"""
        try:
            os.makedirs(os.path.dirname(self.fallback_file), exist_ok=True)
            
            data = {
                "embeddings": embeddings,
                "date_ideas": date_ideas,
                "model_name": self.model_name,
                "created_at": datetime.now().isoformat()
            }
            
            with open(self.fallback_file, "wb") as f:
                pickle.dump(data, f)
            
            logger.info(f"Saved vector store data to {self.fallback_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save to file: {e}")
            return False
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        city: str = None,
        max_price_tier: int = None,
        indoor: bool = None,
        categories: List[str] = None,
        min_duration: int = None,
        max_duration: int = None,
        similarity_threshold: float = 0.1
    ) -> List[Dict[str, Any]]:
        """Search for date ideas using semantic similarity"""
        
        if not self.model:
            logger.warning("Model not loaded - cannot perform search")
            return []
        
        logger.debug(f"🔍 Searching for: '{query}' with filters")
        
        # Create embedding for the query
        try:
            query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
            logger.debug(f"✅ Query embedding created: shape={query_embedding.shape}")
        except Exception as e:
            logger.error(f"Failed to create query embedding: {e}")
            return []
        
        # Try PostgreSQL search first with simple direct query
        if POSTGRESQL_AVAILABLE:
            results = self._search_postgresql_simple(
                query_embedding, top_k, city, max_price_tier, indoor,
                categories, min_duration, max_duration, similarity_threshold
            )
            if results is not None:
                return results
        
        # Fallback to file-based search
        if self.use_fallback:
            return self._search_file_fallback(
                query_embedding, top_k, city, max_price_tier, indoor,
                categories, min_duration, max_duration
            )
        
        logger.warning("No search backend available")
        return []
    
    def _search_postgresql_simple(
        self,
        query_embedding: np.ndarray,
        top_k: int,
        city: str,
        max_price_tier: int,
        indoor: bool,
        categories: List[str],
        min_duration: int,
        max_duration: int,
        similarity_threshold: float
    ) -> Optional[List[Dict[str, Any]]]:
        """Simple PostgreSQL search without complex function calls"""
        try:
            with self.db_config.get_connection() as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    # Build the basic query
                    query = """
                        SELECT 
                            e.event_id,
                            e.title,
                            e.description,
                            l.city,
                            e.price,
                            CASE 
                                WHEN e.price <= 25 THEN 1
                                WHEN e.price <= 75 THEN 2
                                ELSE 3
                            END as price_tier,
                            COALESCE(e.duration_min, 60) as duration_min,
                            COALESCE(e.indoor, false) as indoor,
                            COALESCE(e.kid_friendly, false) as kid_friendly,
                            COALESCE(e.website, '') as website,
                            COALESCE(e.phone, '') as phone,
                            COALESCE(e.rating, 0.0) as rating,
                            COALESCE(e.review_count, 0) as review_count,
                            l.name as venue_name,
                            l.address,
                            (1 - (e.embedding <=> %s::vector(384))) AS similarity_score
                        FROM event e
                        LEFT JOIN location l ON e.location_id = l.location_id
                        WHERE e.embedding IS NOT NULL
                            AND (1 - (e.embedding <=> %s::vector(384))) >= %s
                    """
                    
                    params = [query_embedding.tolist(), query_embedding.tolist(), similarity_threshold]
                    
                    # Add filters
                    if city:
                        query += " AND l.city ILIKE %s"
                        params.append(f"%{city}%")
                    
                    if max_price_tier:
                        max_price_map = {1: 25.0, 2: 75.0, 3: 200.0}
                        max_price = max_price_map.get(max_price_tier, 200.0)
                        query += " AND e.price <= %s"
                        params.append(max_price)
                    
                    if indoor is not None:
                        query += " AND COALESCE(e.indoor, false) = %s"
                        params.append(indoor)
                    
                    if min_duration:
                        query += " AND COALESCE(e.duration_min, 60) >= %s"
                        params.append(min_duration)
                    
                    if max_duration:
                        query += " AND COALESCE(e.duration_min, 60) <= %s"
                        params.append(max_duration)
                    
                    query += " ORDER BY similarity_score DESC LIMIT %s"
                    params.append(top_k)
                    
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    
                    results = []
                    for row in rows:
                        # Get categories for this event
                        cur.execute("""
                            SELECT ec.name 
                            FROM event_category_link ecl 
                            JOIN event_category ec ON ecl.category_id = ec.category_id 
                            WHERE ecl.event_id = %s
                        """, (row[0],))
                        
                        event_categories = [cat[0] for cat in cur.fetchall()]
                        
                        result = {
                            "id": f"event_{row[0]}",
                            "title": row[1],
                            "description": row[2] or "",
                            "categories": event_categories,
                            "city": row[3] or "",
                            "lat": 0.0,  # Not in this query
                            "lon": 0.0,  # Not in this query
                            "price_tier": row[5],
                            "duration_min": row[6],
                            "indoor": row[7],
                            "kid_friendly": row[8],
                            "website": row[9],
                            "phone": row[10],
                            "rating": row[11],
                            "review_count": row[12],
                            "venue_name": row[13] or "",
                            "address": row[14] or "",
                            "similarity_score": float(row[15]),
                            "source": "postgresql_simple"
                        }
                        results.append(result)
                    
                    logger.info(f"Found {len(results)} results from PostgreSQL simple search")
                    return results
                    
        except Exception as e:
            logger.error(f"PostgreSQL simple search failed: {e}")
            return None

    def _search_postgresql(
        self,
        query_embedding: np.ndarray,
        top_k: int,
        city: str,
        max_price_tier: int,
        indoor: bool,
        categories: List[str],
        min_duration: int,
        max_duration: int,
        similarity_threshold: float
    ) -> Optional[List[Dict[str, Any]]]:
        """Search using PostgreSQL with pgvector (Java schema compatible)"""
        try:
            with self.db_config.get_connection() as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    # Convert price_tier to max_price for the search function
                    max_price = None
                    if max_price_tier:
                        price_map = {1: 25.0, 2: 75.0, 3: 200.0}
                        max_price = price_map.get(max_price_tier, 200.0)
                    
                    # Use the Java schema compatible search function
                    cur.execute("""
                        SELECT * FROM search_events_by_similarity(
                            %s::vector(384), %s::real, %s::integer, %s::text, %s::real, %s::boolean, %s::text[], %s::integer, %s::integer
                        )
                    """, (
                        query_embedding.tolist(),
                        similarity_threshold,
                        top_k,
                        city,
                        max_price,
                        indoor,
                        categories,
                        min_duration,
                        max_duration
                    ))
                    
                    results = []
                    for row in cur.fetchall():
                        # Convert database row to dictionary (Java schema format)
                        result = {
                            "id": f"event_{row[0]}",  # event_id
                            "title": row[1],
                            "description": row[2],
                            "categories": row[3],
                            "city": row[4],
                            "lat": row[5],
                            "lon": row[6],
                            "price": float(row[7]) if row[7] else 0.0,
                            "price_tier": row[8],
                            "duration_min": row[9],
                            "indoor": row[10],
                            "kid_friendly": row[11],
                            "website": row[12],
                            "phone": row[13],
                            "rating": float(row[14]) if row[14] else 0.0,
                            "review_count": row[15],
                            "venue_name": row[16],
                            "address": row[17],
                            "similarity_score": float(row[18]),
                            "source": "postgresql_java_schema",
                            "is_ai_recommended": row[19],
                            "ai_score": float(row[20]) if row[20] else 0.0,
                            "popularity": row[21] if row[21] else 0
                        }
                        
                        # Add entity references
                        result["entity_references"] = self._build_entity_references(result)
                        
                        results.append(result)
                    
                    logger.info(f"Found {len(results)} results from PostgreSQL (Java schema)")
                    return results
                    
        except Exception as e:
            logger.error(f"PostgreSQL search failed: {e}")
            return None
    
    def _search_file_fallback(
        self,
        query_embedding: np.ndarray,
        top_k: int,
        city: str,
        max_price_tier: int,
        indoor: bool,
        categories: List[str],
        min_duration: int,
        max_duration: int
    ) -> List[Dict[str, Any]]:
        """Fallback search using pickle file"""
        # Load data from file if not already loaded
        try:
            if not os.path.exists(self.fallback_file):
                logger.warning("No fallback data file found")
                return []
            
            with open(self.fallback_file, "rb") as f:
                data = pickle.load(f)
            
            embeddings = data.get("embeddings")
            date_ideas = data.get("date_ideas", [])
            
            if embeddings is None or len(date_ideas) == 0:
                logger.warning("No data in fallback file")
                return []
            
            # Calculate similarities
            similarities = np.dot(embeddings, query_embedding)
            sorted_indices = np.argsort(similarities)[::-1]
            
            results = []
            for idx in sorted_indices[:top_k]:
                date_idea = date_ideas[idx].copy()
                similarity_score = float(similarities[idx])
                
                # Apply filters (simplified version)
                if city and date_idea.get("city", "").lower() != city.lower():
                    continue
                if max_price_tier and date_idea.get("price_tier", 1) > max_price_tier:
                    continue
                if indoor is not None and date_idea.get("indoor") != indoor:
                    continue
                
                date_idea["similarity_score"] = similarity_score
                date_idea["source"] = "file_fallback"
                date_idea["entity_references"] = self._build_entity_references(date_idea)
                results.append(date_idea)
            
            logger.info(f"Found {len(results)} results from file fallback")
            return results
            
        except Exception as e:
            logger.error(f"File fallback search failed: {e}")
            return []
    
    def _build_entity_references(self, date_idea: Dict[str, Any]) -> Dict[str, Any]:
        """Build entity references for a date idea"""
        primary_entity = {
            "id": date_idea.get("id", ""),
            "type": "date_idea",
            "title": date_idea.get("title", ""),
            "url": f"/api/date-ideas/{date_idea.get('id', '')}"
        }
        
        related_entities = []
        
        # Add venue if available
        if date_idea.get("venue_id") and date_idea.get("venue_name"):
            related_entities.append({
                "id": date_idea["venue_id"],
                "type": "venue",
                "title": date_idea["venue_name"],
                "url": f"/api/venues/{date_idea['venue_id']}"
            })
        
        # Add business if available
        if date_idea.get("business_id") and date_idea.get("business_name"):
            related_entities.append({
                "id": date_idea["business_id"],
                "type": "business",
                "title": date_idea["business_name"],
                "url": f"/api/businesses/{date_idea['business_id']}"
            })
        
        # Add city
        if date_idea.get("city"):
            city_id = date_idea.get("city_id", date_idea["city"].lower().replace(" ", "_"))
            related_entities.append({
                "id": city_id,
                "type": "city",
                "title": date_idea["city"],
                "url": f"/api/cities/{city_id}"
            })
        
        return {
            "primary_entity": primary_entity,
            "related_entities": related_entities
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        stats = {
            "model_name": self.model_name,
            "model_loaded": self.model is not None,
            "postgresql_available": POSTGRESQL_AVAILABLE,
            "use_fallback": self.use_fallback
        }
        
        # Try to get count from PostgreSQL
        if POSTGRESQL_AVAILABLE:
            try:
                with self.db_config.get_connection() as conn:
                    with conn.cursor() as cur:
                        # Count events with embeddings
                        cur.execute("SELECT COUNT(*) FROM event WHERE embedding IS NOT NULL")
                        embedding_count = cur.fetchone()[0]
                        
                        # Count total events
                        cur.execute("SELECT COUNT(*) FROM event")
                        total_count = cur.fetchone()[0]
                        
                        # Count locations and categories
                        cur.execute("SELECT COUNT(*) FROM location")
                        location_count = cur.fetchone()[0]
                        
                        cur.execute("SELECT COUNT(*) FROM event_category")
                        category_count = cur.fetchone()[0]
                        
                        stats.update({
                            "postgresql_events_with_embeddings": embedding_count,
                            "postgresql_total_events": total_count,
                            "postgresql_locations": location_count,
                            "postgresql_categories": category_count
                        })
            except Exception as e:
                stats["postgresql_error"] = str(e)
        
        # Try to get count from fallback file
        if self.use_fallback and os.path.exists(self.fallback_file):
            try:
                with open(self.fallback_file, "rb") as f:
                    data = pickle.load(f)
                    stats["fallback_count"] = len(data.get("date_ideas", []))
            except Exception as e:
                stats["fallback_error"] = str(e)
        
        return stats


# Global instance
_vector_store = None

def get_vector_store() -> PostgreSQLVectorStore:
    """Get global vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = PostgreSQLVectorStore()
    return _vector_store