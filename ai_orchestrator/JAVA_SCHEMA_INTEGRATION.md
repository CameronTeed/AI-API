# Java Schema Integration Guide

This guide explains how the AI Orchestrator integrates with your existing Java application database schema.

## Schema Integration

### Your Existing Java Schema ✅
Your Java application uses these tables:
- `event` - Core event/date idea data
- `location` - Location and venue information  
- `event_category` - Categories (Romantic, Adventure, etc.)
- `event_category_link` - Many-to-many event ↔ category relationships
- `related_event` - Event relationships
- `ai_recommendation` - AI recommendation storage

### Enhanced Schema for Vector Search 🚀
The PostgreSQL setup enhances your existing schema by:

1. **Adding vector columns** to the `event` table:
   ```sql
   ALTER TABLE event ADD COLUMN embedding vector(384);
   ALTER TABLE event ADD COLUMN duration_min INTEGER;
   ALTER TABLE event ADD COLUMN indoor BOOLEAN;
   ALTER TABLE event ADD COLUMN kid_friendly BOOLEAN;
   ALTER TABLE event ADD COLUMN website TEXT;
   ALTER TABLE event ADD COLUMN phone TEXT;
   ALTER TABLE event ADD COLUMN rating REAL;
   ALTER TABLE event ADD COLUMN review_count INTEGER;
   ALTER TABLE event ADD COLUMN metadata JSONB DEFAULT '{}'::jsonb;
   ```

2. **Adding coordinates** to the `location` table:
   ```sql
   ALTER TABLE location ADD COLUMN lat REAL;
   ALTER TABLE location ADD COLUMN lon REAL;
   ```

3. **Creating compatibility views** that map Java schema to AI Orchestrator format:
   ```sql
   CREATE VIEW date_ideas AS SELECT ... FROM event e LEFT JOIN location l ...
   ```

## Data Flow

### 1. Java Application → PostgreSQL
Your Java application continues to work normally:
```java
// Your existing Java code works unchanged
Event event = new Event();
event.setTitle("Romantic Dinner");
event.setDescription("Cozy restaurant with great atmosphere");
event.setPrice(75.00);
eventRepository.save(event);
```

### 2. AI Orchestrator → PostgreSQL
The Python AI Orchestrator reads from the same database:
```python
# AI Orchestrator can search your Java data
vector_store = get_vector_store()
results = vector_store.search("romantic dinner for two")
```

### 3. Vector Embeddings
When you populate the vector store, it:
- Reads your existing events from the `event` table
- Creates semantic embeddings using sentence transformers
- Stores embeddings in the `embedding` column
- Uses pgvector for fast similarity search

## Integration Points

### Database Connection
Both applications can share the same PostgreSQL database:

**Java (application.properties):**
```properties
spring.datasource.url=jdbc:postgresql://localhost:5432/ai_orchestrator
spring.datasource.username=postgres
spring.datasource.password=postgres
```

**Python (.env):**
```bash
DB_HOST=localhost
DB_NAME=ai_orchestrator
DB_USER=postgres
DB_PASSWORD=postgres
```

### API Integration
You can integrate the AI search with your Java application via:

1. **gRPC** (recommended for high performance):
   ```java
   // Your Java app calls the Python AI service
   ChatServiceGrpc.ChatServiceBlockingStub stub = ...;
   ChatRequest request = ChatRequest.newBuilder()
       .addMessages(ChatMessage.newBuilder()
           .setRole("user")
           .setContent("find romantic restaurants")
           .build())
       .build();
   ChatResponse response = stub.chat(request);
   ```

2. **REST API** (easier integration):
   ```java
   // Your Java app calls the REST wrapper
   RestTemplate restTemplate = new RestTemplate();
   String url = "http://localhost:8000/chat";
   ChatRequest request = new ChatRequest("find romantic restaurants");
   ChatResponse response = restTemplate.postForObject(url, request, ChatResponse.class);
   ```

### Data Synchronization

#### Option 1: Real-time Sync (Recommended)
Set up triggers to update embeddings when events change:
```sql
CREATE OR REPLACE FUNCTION refresh_event_embedding()
RETURNS TRIGGER AS $$
BEGIN
    -- Mark for re-embedding (AI service will pick this up)
    NEW.embedding = NULL;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER event_embedding_refresh
    BEFORE UPDATE ON event
    FOR EACH ROW
    WHEN (OLD.title != NEW.title OR OLD.description != NEW.description)
    EXECUTE FUNCTION refresh_event_embedding();
```

#### Option 2: Batch Sync
Run periodic updates:
```bash
# Update embeddings for all events without embeddings
python populate_vector_store.py --update-missing
```

## Migration Steps

### 1. Backup Your Database
```bash
pg_dump your_database > backup.sql
```

### 2. Apply Schema Enhancements
```bash
# Run the enhanced schema (safe - won't delete existing data)
python init_database.py
```

### 3. Populate Vector Store
```bash
# Create embeddings for existing events
python populate_vector_store.py
```

### 4. Test Integration
```bash
# Test search functionality
python -c "
from server.tools.vector_store import get_vector_store
vs = get_vector_store()
results = vs.search('romantic dinner')
for r in results:
    print(f'Event ID: {r[\"id\"]}, Title: {r[\"title\"]}')
"
```

## Search Features

### Semantic Search
Find events using natural language:
```python
# These all find similar results
results = vector_store.search("romantic evening")
results = vector_store.search("date night ideas")  
results = vector_store.search("intimate dinner")
```

### Advanced Filtering
Combine semantic search with structured filters:
```python
results = vector_store.search(
    query="fun activities",
    city="Ottawa",
    max_price_tier=2,  # $ or $$, not $$$
    indoor=True,       # indoor only
    categories=["family", "entertainment"],
    min_duration=60,   # at least 1 hour
    max_duration=180   # at most 3 hours
)
```

### Java Integration Example
```java
@Service
public class EventSearchService {
    
    @Autowired
    private EventRepository eventRepository;
    
    private final ChatServiceGrpc.ChatServiceBlockingStub aiStub;
    
    public List<Event> searchEventsSemanically(String query, String city, Integer maxPrice) {
        // Call AI Orchestrator
        ChatRequest request = ChatRequest.newBuilder()
            .addMessages(ChatMessage.newBuilder()
                .setRole("user")
                .setContent(query)
                .build())
            .setConstraints(Constraints.newBuilder()
                .setCity(city)
                .setBudgetTier(maxPrice)
                .build())
            .build();
            
        ChatResponse response = aiStub.chat(request);
        
        // Extract event IDs from AI response
        List<Long> eventIds = response.getStructured().getOptionsList()
            .stream()
            .map(option -> extractEventId(option.getEntityReferences().getPrimaryEntity().getId()))
            .collect(Collectors.toList());
            
        // Fetch full event objects from your repository
        return eventRepository.findAllById(eventIds);
    }
    
    private Long extractEventId(String aiId) {
        // Convert "event_123" -> 123
        return Long.parseLong(aiId.replace("event_", ""));
    }
}
```

## Performance Considerations

### Indexing
The schema creates optimal indexes for both Java queries and vector search:
```sql
-- Java application indexes
CREATE INDEX idx_event_location ON event (location_id);
CREATE INDEX idx_event_price ON event (price);
CREATE INDEX idx_event_category_link_event ON event_category_link (event_id);

-- Vector search indexes  
CREATE INDEX idx_event_embedding ON event USING hnsw (embedding vector_cosine_ops);
```

### Connection Pooling
Both applications can share the same connection pool or use separate pools:

**Java (HikariCP):**
```properties
spring.datasource.hikari.maximum-pool-size=20
spring.datasource.hikari.minimum-idle=5
```

**Python:**
```bash
DB_MIN_CONNECTIONS=5
DB_MAX_CONNECTIONS=15
```

## Monitoring & Maintenance

### Vector Embedding Health
Monitor embedding coverage:
```sql
SELECT 
    COUNT(*) as total_events,
    COUNT(embedding) as events_with_embeddings,
    ROUND(COUNT(embedding) * 100.0 / COUNT(*), 2) as coverage_percent
FROM event;
```

### Search Performance
Monitor search performance:
```sql
-- Enable query logging for slow queries
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();
```

### Embedding Updates
Set up automated embedding updates:
```bash
# Crontab entry to refresh embeddings nightly
0 2 * * * cd /path/to/ai_orchestrator && python populate_vector_store.py --update-missing
```

## Troubleshooting

### Common Issues

1. **"No embeddings found"**
   - Run: `python populate_vector_store.py`
   - Check: `SELECT COUNT(*) FROM event WHERE embedding IS NOT NULL;`

2. **"Java app can't find events"**
   - Events created by AI have `is_ai_recommended = true`
   - Filter in Java: `WHERE is_ai_recommended = false` for user-created events

3. **"Performance is slow"**
   - Check indexes: `EXPLAIN ANALYZE SELECT ...`
   - Tune HNSW parameters: `WITH (m = 32, ef_construction = 128)`

4. **"Search returns no results"**
   - Lower similarity threshold: `similarity_threshold = 0.1`
   - Check embedding model: sentence transformers must be consistent

### Debug Queries
```sql
-- Check schema compatibility
SELECT * FROM enhanced_events_view LIMIT 5;

-- Check embedding distribution
SELECT COUNT(*), AVG(array_length(embedding::real[], 1)) FROM event WHERE embedding IS NOT NULL;

-- Test vector search directly
SELECT title, (1 - (embedding <=> '[0.1,0.2,...]'::vector)) as similarity 
FROM event 
WHERE embedding IS NOT NULL 
ORDER BY similarity DESC 
LIMIT 5;
```

This integration allows your Java application and AI Orchestrator to work together seamlessly while maintaining data consistency and performance.