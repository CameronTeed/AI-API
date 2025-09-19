# PostgreSQL Vector Store Setup Guide

This guide explains how to connect your AI Orchestrator vector storage to PostgreSQL using pgvector.

## Prerequisites

1. **PostgreSQL 14+** with **pgvector extension**
2. **Python 3.11+**
3. **Required Python packages** (see requirements.txt)

## Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file or set environment variables:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=ai_orchestrator
export DB_USER=postgres
export DB_PASSWORD=your_password
```

### 3. Initialize Database

```bash
python init_database.py
```

This script will:
- Create the pgvector extension
- Create the `date_ideas` table with vector columns
- Set up indexes for fast similarity search
- Create stored functions for search

### 4. Populate Vector Store

```bash
python populate_vector_store.py
```

This will load sample data and create embeddings in PostgreSQL.

### 5. (Optional) Migrate Existing Data

If you have existing pickle-based data:

```bash
python migrate_to_postgresql.py
```

## Database Schema

The main table structure:

```sql
CREATE TABLE date_ideas (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    categories TEXT[],
    city TEXT,
    lat REAL,
    lon REAL,
    price_tier INTEGER,
    duration_min INTEGER,
    indoor BOOLEAN,
    kid_friendly BOOLEAN,
    website TEXT,
    phone TEXT,
    rating REAL,
    review_count INTEGER,
    
    -- Vector embedding (384 dimensions for all-MiniLM-L6-v2)
    embedding vector(384),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Vector Search Features

- **Semantic Search**: Natural language queries like "romantic dinner for two"
- **Filtering**: City, price tier, indoor/outdoor, categories, duration
- **Similarity Scoring**: Results ranked by semantic relevance (cosine similarity)
- **Fast Search**: HNSW index for approximate nearest neighbor search
- **Fallback Support**: Automatic fallback to file-based storage if PostgreSQL unavailable

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | localhost | PostgreSQL host |
| `DB_PORT` | 5432 | PostgreSQL port |
| `DB_NAME` | ai_orchestrator | Database name |
| `DB_USER` | postgres | Database user |
| `DB_PASSWORD` | postgres | Database password |
| `DB_MIN_CONNECTIONS` | 1 | Min connection pool size |
| `DB_MAX_CONNECTIONS` | 10 | Max connection pool size |

### Vector Store Options

The vector store automatically detects PostgreSQL availability and falls back to file-based storage if needed.

```python
from server.tools.vector_store import get_vector_store

# Get vector store (PostgreSQL + file fallback)
vector_store = get_vector_store()

# Search with filters
results = vector_store.search(
    query="romantic dinner",
    city="Ottawa",
    max_price_tier=2,
    indoor=None,
    categories=["romantic"],
    top_k=10
)
```

## PostgreSQL Setup

### Install PostgreSQL with pgvector

**Ubuntu/Debian:**
```bash
sudo apt install postgresql postgresql-contrib
sudo apt install postgresql-14-pgvector
```

**macOS with Homebrew:**
```bash
brew install postgresql
brew install pgvector
```

**Docker:**
```bash
docker run -d \
  --name ai-orchestrator-db \
  -e POSTGRES_DB=ai_orchestrator \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### Manual Extension Install

If pgvector isn't available via package manager:

```sql
-- Connect as superuser
CREATE EXTENSION IF NOT EXISTS vector;
```

## Testing the Setup

Test database connectivity:
```bash
python -c "from server.db_config import test_connection; print('Success!' if test_connection() else 'Failed!')"
```

Test vector search:
```bash
python -c "
from server.tools.vector_store import get_vector_store
vs = get_vector_store()
results = vs.search('romantic dinner', top_k=3)
print(f'Found {len(results)} results')
for r in results: print(f'- {r[\"title\"]}')
"
```

## Performance Tuning

### Index Configuration

The schema creates an HNSW index for fast similarity search:

```sql
CREATE INDEX idx_date_ideas_embedding ON date_ideas 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);
```

Adjust parameters for your data size:
- `m`: Controls index quality vs size (higher = better quality, larger index)
- `ef_construction`: Controls build time vs quality

### Query Performance

For best performance:
1. Use filters to reduce search space
2. Limit `top_k` to reasonable values (≤50)
3. Use connection pooling for high-traffic applications
4. Monitor query performance with PostgreSQL's query analyzer

## Troubleshooting

### Common Issues

1. **"pgvector extension not found"**
   - Install pgvector extension: `sudo apt install postgresql-14-pgvector`
   - Or use Docker image with pgvector included

2. **"Permission denied"**
   - Ensure user has CREATE permissions on database
   - Grant necessary permissions: `GRANT ALL ON SCHEMA public TO your_user;`

3. **"Connection failed"**
   - Check PostgreSQL is running: `sudo systemctl status postgresql`
   - Verify connection parameters in environment variables
   - Check firewall/network configuration

4. **"Model not loaded"**
   - Install sentence-transformers: `pip install sentence-transformers`
   - Check internet connectivity for model download

### Monitoring

Check vector store status:
```python
from server.tools.vector_store import get_vector_store
stats = get_vector_store().get_stats()
print(stats)
```

Monitor database queries:
```sql
-- Enable query logging in postgresql.conf
log_statement = 'all'
log_min_duration_statement = 1000  -- Log slow queries
```

## Migration Notes

- File-based pickle storage is still supported as fallback
- Existing applications continue to work without changes
- Vector store automatically chooses best available backend
- Data can be migrated from pickle files using `migrate_to_postgresql.py`

## API Integration

The vector store integrates seamlessly with existing code:

```python
# Existing code continues to work
from server.tools.vector_store import get_vector_store

vector_store = get_vector_store()
results = vector_store.search("fun date ideas", top_k=5)
```

The backend (PostgreSQL vs file) is transparent to the application layer.