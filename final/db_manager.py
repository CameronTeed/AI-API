# db_manager.py
# PostgreSQL database manager for venue data
# handles all database operations: CRUD, search, filtering, semantic search
# uses pgvector for semantic similarity search

import os
import pandas as pd
from typing import List, Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2.pool import SimpleConnectionPool
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables from parent directory
_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(_env_path):
    load_dotenv(_env_path)

# Initialize connection pool
_pool = None
_embedding_model = None

def init_db_pool(host=None, database=None, user=None, password=None, port=5432, min_conn=2, max_conn=10):
    """Initialize database connection pool"""
    global _pool

    host = host or os.getenv('DB_HOST', 'localhost')
    database = database or os.getenv('DB_NAME', 'sparkdates')
    user = user or os.getenv('DB_USER', 'postgres')
    password = password or os.getenv('DB_PASSWORD', 'postgres')
    port = int(os.getenv('DB_PORT', port))

    try:
        _pool = SimpleConnectionPool(
            min_conn, max_conn,
            host=host,
            database=database,
            user=user,
            password=password,
            port=port
        )
        print(f"✓ Database pool initialized: {database}@{host}:{port}")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize database pool: {e}")
        return False

def get_connection():
    """Get a connection from the pool"""
    if _pool is None:
        init_db_pool()
    return _pool.getconn()

def return_connection(conn):
    """Return a connection to the pool"""
    if _pool:
        _pool.putconn(conn)

def init_embedding_model(model_name='all-MiniLM-L6-v2'):
    """Initialize sentence transformer for embeddings"""
    global _embedding_model
    try:
        _embedding_model = SentenceTransformer(model_name)
        print(f"✓ Embedding model loaded: {model_name}")
        return True
    except Exception as e:
        print(f"✗ Failed to load embedding model: {e}")
        return False

def get_embedding(text: str) -> List[float]:
    """Get embedding for text"""
    if _embedding_model is None:
        init_embedding_model()

    if text is None or text == "":
        text = "venue"

    embedding = _embedding_model.encode(text, convert_to_numpy=True)
    return embedding.tolist()

def create_tables():
    """Create necessary database tables"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Enable pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Venues table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS venues (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    address TEXT,
                    short_address VARCHAR(255),
                    lat FLOAT,
                    lon FLOAT,
                    rating FLOAT DEFAULT 0,
                    reviews_count INT DEFAULT 0,
                    price_level VARCHAR(50),
                    cost INT DEFAULT 30,
                    primary_type VARCHAR(100),
                    primary_type_display_name VARCHAR(255),
                    all_types TEXT,
                    type VARCHAR(100),
                    google_maps_uri TEXT,
                    website_uri TEXT,
                    regular_opening_hours TEXT,
                    current_opening_hours TEXT,
                    description TEXT,
                    review TEXT,
                    review_summary TEXT,
                    neighborhood_summary TEXT,
                    true_vibe VARCHAR(255),
                    serves_dessert BOOLEAN DEFAULT FALSE,
                    serves_coffee BOOLEAN DEFAULT FALSE,
                    serves_beer BOOLEAN DEFAULT FALSE,
                    serves_wine BOOLEAN DEFAULT FALSE,
                    serves_cocktails BOOLEAN DEFAULT FALSE,
                    serves_vegetarian BOOLEAN DEFAULT FALSE,
                    serves_breakfast BOOLEAN DEFAULT FALSE,
                    serves_brunch BOOLEAN DEFAULT FALSE,
                    serves_lunch BOOLEAN DEFAULT FALSE,
                    serves_dinner BOOLEAN DEFAULT FALSE,
                    good_for_groups BOOLEAN DEFAULT FALSE,
                    good_for_children BOOLEAN DEFAULT FALSE,
                    good_for_watching_sports BOOLEAN DEFAULT FALSE,
                    live_music BOOLEAN DEFAULT FALSE,
                    outdoor_seating BOOLEAN DEFAULT FALSE,
                    allows_dogs BOOLEAN DEFAULT FALSE,
                    reservable BOOLEAN DEFAULT FALSE,
                    takeout BOOLEAN DEFAULT FALSE,
                    delivery BOOLEAN DEFAULT FALSE,
                    dine_in BOOLEAN DEFAULT FALSE,
                    description_embedding vector(384),
                    name_embedding vector(384),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_venues_type ON venues(type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_venues_vibe ON venues(true_vibe)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_venues_rating ON venues(rating DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_venues_cost ON venues(cost)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_venues_location ON venues(lat, lon)")

            # Vibe keywords table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vibe_keywords (
                    id SERIAL PRIMARY KEY,
                    vibe VARCHAR(100) NOT NULL,
                    keyword VARCHAR(255) NOT NULL,
                    frequency INT DEFAULT 1,
                    is_learned BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(vibe, keyword)
                )
            """)

            # Search history table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id SERIAL PRIMARY KEY,
                    query TEXT NOT NULL,
                    predicted_vibes VARCHAR(255),
                    num_results INT,
                    user_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            print("✓ Database tables created successfully")
            return True
    except Exception as e:
        conn.rollback()
        print(f"✗ Error creating tables: {e}")
        return False
    finally:
        return_connection(conn)


def insert_venues(venues: List[Dict]) -> int:
    """Insert venues into database, handling duplicates"""
    if not venues:
        return 0

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            inserted = 0
            for venue in venues:
                # Get embeddings
                desc_embedding = get_embedding(venue.get('description', ''))
                name_embedding = get_embedding(venue.get('name', ''))

                # Prepare data
                data = (
                    venue.get('id'),
                    venue.get('name'),
                    venue.get('address'),
                    venue.get('short_address'),
                    venue.get('lat'),
                    venue.get('lon'),
                    venue.get('rating', 0),
                    venue.get('reviews_count', 0),
                    venue.get('price_level'),
                    venue.get('cost', 30),
                    venue.get('primary_type'),
                    venue.get('primary_type_display_name'),
                    venue.get('all_types'),
                    venue.get('type'),
                    venue.get('google_maps_uri'),
                    venue.get('website_uri'),
                    venue.get('regular_opening_hours', ''),
                    venue.get('current_opening_hours', ''),
                    venue.get('description'),
                    venue.get('review'),
                    venue.get('review_summary'),
                    venue.get('neighborhood_summary'),
                    venue.get('true_vibe', 'casual'),
                    venue.get('serves_dessert', False),
                    venue.get('serves_coffee', False),
                    venue.get('serves_beer', False),
                    venue.get('serves_wine', False),
                    venue.get('serves_cocktails', False),
                    venue.get('serves_vegetarian', False),
                    venue.get('serves_breakfast', False),
                    venue.get('serves_brunch', False),
                    venue.get('serves_lunch', False),
                    venue.get('serves_dinner', False),
                    venue.get('good_for_groups', False),
                    venue.get('good_for_children', False),
                    venue.get('good_for_watching_sports', False),
                    venue.get('live_music', False),
                    venue.get('outdoor_seating', False),
                    venue.get('allows_dogs', False),
                    venue.get('reservable', False),
                    venue.get('takeout', False),
                    venue.get('delivery', False),
                    venue.get('dine_in', False),
                    desc_embedding,
                    name_embedding,
                )

                # Upsert
                cur.execute("""
                    INSERT INTO venues (
                        id, name, address, short_address, lat, lon, rating, reviews_count,
                        price_level, cost, primary_type, primary_type_display_name, all_types,
                        type, google_maps_uri, website_uri, regular_opening_hours, current_opening_hours,
                        description, review, review_summary, neighborhood_summary, true_vibe,
                        serves_dessert, serves_coffee, serves_beer, serves_wine, serves_cocktails,
                        serves_vegetarian, serves_breakfast, serves_brunch, serves_lunch, serves_dinner,
                        good_for_groups, good_for_children, good_for_watching_sports, live_music,
                        outdoor_seating, allows_dogs, reservable, takeout, delivery, dine_in,
                        description_embedding, name_embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        updated_at = CURRENT_TIMESTAMP
                """, data)
                inserted += 1

            conn.commit()
            print(f"✓ Inserted {inserted} venues into database")
            return inserted
    except Exception as e:
        conn.rollback()
        print(f"✗ Error inserting venues: {e}")
        return 0
    finally:
        return_connection(conn)

def get_all_venues() -> pd.DataFrame:
    """Get all venues as DataFrame"""
    conn = get_connection()
    try:
        query = "SELECT * FROM venues ORDER BY rating DESC"
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        print(f"✗ Error fetching venues: {e}")
        return pd.DataFrame()
    finally:
        return_connection(conn)

def get_venues_for_ga(vibes: List[str] = None, types: List[str] = None,
                      max_cost: int = None, min_rating: float = 0,
                      limit: int = 500) -> pd.DataFrame:
    """
    OPTIMIZED: Get venues for genetic algorithm with smart filtering.

    Loads only needed columns and filters at database level.
    Much faster than get_all_venues() for GA operations.

    Args:
        vibes: List of target vibes to filter by
        types: List of target types to filter by
        max_cost: Maximum cost filter
        min_rating: Minimum rating filter
        limit: Maximum number of venues to return

    Returns:
        DataFrame with venues optimized for GA
    """
    conn = get_connection()
    try:
        # Only load columns needed for GA (not all 40+ columns)
        # Includes Google Places info for frontend display
        columns = [
            'id', 'name', 'address', 'short_address', 'lat', 'lon', 'rating', 'reviews_count', 'cost',
            'type', 'all_types', 'primary_type_display_name', 'true_vibe',
            'serves_dessert', 'serves_coffee', 'serves_beer', 'serves_wine',
            'serves_cocktails', 'good_for_groups', 'good_for_children',
            'live_music', 'outdoor_seating', 'allows_dogs', 'reservable',
            'google_maps_uri', 'website_uri', 'regular_opening_hours', 'current_opening_hours',
            'description', 'review_summary', 'price_level'
        ]
        columns_str = ', '.join(columns)

        sql = f"SELECT {columns_str} FROM venues WHERE 1=1"
        params = []

        # Filter by vibes at database level
        if vibes:
            vibe_conditions = " OR ".join([f"true_vibe ILIKE %s" for _ in vibes])
            sql += f" AND ({vibe_conditions})"
            params.extend([f"%{v}%" for v in vibes])

        # Filter by types at database level
        if types:
            type_conditions = " OR ".join([f"type ILIKE %s" for _ in types])
            sql += f" AND ({type_conditions})"
            params.extend([f"%{t}%" for t in types])

        # Filter by cost at database level
        if max_cost:
            sql += " AND cost <= %s"
            params.append(max_cost)

        # Filter by rating at database level
        if min_rating > 0:
            sql += " AND rating >= %s"
            params.append(min_rating)

        # Order by rating and limit
        sql += " ORDER BY rating DESC LIMIT %s"
        params.append(limit)

        df = pd.read_sql(sql, conn, params=params)
        return df
    except Exception as e:
        print(f"✗ Error fetching venues for GA: {e}")
        return pd.DataFrame()
    finally:
        return_connection(conn)

def search_venues(
    query: str = None,
    vibes: List[str] = None,
    types: List[str] = None,
    min_rating: float = 0,
    max_cost: int = None,
    limit: int = 50
) -> pd.DataFrame:
    """Search venues with multiple filters"""
    conn = get_connection()
    try:
        sql = "SELECT * FROM venues WHERE 1=1"
        params = []

        if vibes:
            vibe_conditions = " OR ".join([f"true_vibe ILIKE %s" for _ in vibes])
            sql += f" AND ({vibe_conditions})"
            params.extend([f"%{v}%" for v in vibes])

        if types:
            type_conditions = " OR ".join([f"type ILIKE %s" for _ in types])
            sql += f" AND ({type_conditions})"
            params.extend([f"%{t}%" for t in types])

        if min_rating > 0:
            sql += " AND rating >= %s"
            params.append(min_rating)

        if max_cost:
            sql += " AND cost <= %s"
            params.append(max_cost)

        sql += " ORDER BY rating DESC LIMIT %s"
        params.append(limit)

        df = pd.read_sql(sql, conn, params=params)
        return df
    except Exception as e:
        print(f"✗ Error searching venues: {e}")
        return pd.DataFrame()
    finally:
        return_connection(conn)

def get_venue_by_id(venue_id: str) -> Optional[Dict]:
    """Get a single venue by ID"""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM venues WHERE id = %s", (venue_id,))
            result = cur.fetchone()
            return dict(result) if result else None
    except Exception as e:
        print(f"✗ Error fetching venue: {e}")
        return None
    finally:
        return_connection(conn)

def update_venue_vibe(venue_id: str, vibe: str) -> bool:
    """Update a venue's vibe classification"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE venues SET true_vibe = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (vibe, venue_id)
            )
            conn.commit()
            return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"✗ Error updating venue vibe: {e}")
        return False
    finally:
        return_connection(conn)

def log_search(query: str, predicted_vibes: List[str], num_results: int, user_id: str = None):
    """Log a search for analytics"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO search_history (query, predicted_vibes, num_results, user_id)
                   VALUES (%s, %s, %s, %s)""",
                (query, ",".join(predicted_vibes) if predicted_vibes else None, num_results, user_id)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"✗ Error logging search: {e}")
    finally:
        return_connection(conn)

def close_pool():
    """Close all connections in the pool"""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        print("✓ Database pool closed")


