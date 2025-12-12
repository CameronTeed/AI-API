# PostgreSQL Database Setup for SparkDates

## Overview

The final folder has been upgraded to use PostgreSQL instead of CSV files. This provides:
- **Scalability**: Handle thousands of venues efficiently
- **Semantic Search**: pgvector support for intelligent venue matching
- **Dynamic Learning**: Store and learn from vibe keywords and type mappings
- **Analytics**: Track search history and user preferences
- **Caching**: Smart in-memory caching to reduce database queries

## Prerequisites

1. **PostgreSQL 13+** with pgvector extension
2. **Python 3.8+** with required packages:
   ```bash
   pip install psycopg2-binary pandas sentence-transformers scikit-learn spacy
   python -m spacy download en_core_web_md
   ```

## Environment Setup

Create a `.env` file in the `final/` directory:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sparkdates
DB_USER=postgres
DB_PASSWORD=your_password
GOOGLE_PLACES_API_KEY=your_api_key
```

## Database Initialization

### 1. Create Database

```bash
createdb sparkdates
psql sparkdates -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 2. Seed Database

**Option A: From Google Places API**
```bash
python seed_database.py --api --verify
```

**Option B: From Existing CSV**
```bash
python seed_database.py --csv ottawa_venues.csv --verify
```

**Option C: Default (CSV if exists, else API)**
```bash
python seed_database.py --verify
```

## Database Schema

### venues table
- **id**: Unique venue identifier (Primary Key)
- **name, address, lat, lon**: Location information
- **rating, reviews_count**: Quality metrics
- **cost**: Average cost in dollars
- **type, primary_type**: Venue classification
- **true_vibe**: Predicted vibe(s)
- **description, review**: Text content for ML
- **Boolean features**: serves_dessert, serves_coffee, outdoor_seating, etc.
- **Embeddings**: description_embedding, name_embedding (pgvector)
- **Timestamps**: created_at, updated_at

### vibe_keywords table
- Stores learned vibe keywords from data
- Tracks frequency and whether keyword was learned

### search_history table
- Logs all searches for analytics
- Tracks predicted vibes and results count

## Usage

### In Python Code

```python
import db_manager

# Initialize
db_manager.init_db_pool()
db_manager.init_embedding_model()

# Get all venues
df = db_manager.get_all_venues()

# Search with filters
results = db_manager.search_venues(
    vibes=['romantic'],
    types=['restaurant'],
    min_rating=4.0,
    max_cost=100,
    limit=20
)

# Get single venue
venue = db_manager.get_venue_by_id('venue_id')

# Update vibe
db_manager.update_venue_vibe('venue_id', 'romantic')

# Log search
db_manager.log_search('romantic dinner', ['romantic'], 5)

# Close connections
db_manager.close_pool()
```

### Planners

Both heuristic and genetic algorithm planners now automatically:
1. Load from database if no venues_df provided
2. Fall back to CSV if database unavailable
3. Work seamlessly with database-loaded data

```python
import heuristic_planner

result = heuristic_planner.plan_date({
    'vibe': 'romantic',
    'budget_range': (50, 150),
    'max_venues': 5
})
```

### NLP Classifier

Train classifier from database:
```python
import nlp_classifier

vectorizer, clf = nlp_classifier.train_vibe_classifier('database')
```

## Caching

Smart caching reduces redundant computations:

```python
import cache_manager

# Get cache stats
stats = cache_manager.get_cache_stats()
print(f"Cached items: {stats['total_items']}")

# Clean up expired cache
removed = cache_manager.cleanup_expired_cache()

# Clear specific cache
cache_manager.clear_cache('vibe')  # or 'search', 'venue', 'all'
```

## Performance Tips

1. **Indexes**: Database automatically creates indexes on frequently queried columns
2. **Embeddings**: Cached in database for fast semantic search
3. **Connection Pool**: Reuses connections to reduce overhead
4. **TTL Caching**: Vibe predictions cached for 24 hours, searches for 1 hour

## Troubleshooting

**Connection Error**: Check DB_HOST, DB_PORT, DB_USER, DB_PASSWORD in .env

**pgvector not found**: Install extension: `psql sparkdates -c "CREATE EXTENSION vector;"`

**No venues in database**: Run `python seed_database.py --api` to fetch from Google Places

**Slow queries**: Run `ANALYZE;` in psql to update query planner statistics

