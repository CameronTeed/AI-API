# Flyway Integration Guide for AI Orchestrator

This guide explains how to integrate the AI Orchestrator vector search capabilities into your Java application using Flyway migrations.

## Migration Files Overview

The AI Orchestrator integration consists of 5 Flyway migration files:

1. **V1.1.0** - Add pgvector extension
2. **V1.2.0** - Enhance location table with coordinates  
3. **V1.3.0** - Enhance event table with AI fields
4. **V1.4.0** - Add vector search functions
5. **V1.5.0** - Create enhanced views

## Setup Instructions

### 1. Copy Migration Files to Your Java Project

Copy the migration files to your Java project's Flyway migrations directory:

```bash
# Copy from AI Orchestrator to your Java project
cp /path/to/ai_orchestrator/flyway/* /path/to/your-java-project/src/main/resources/db/migration/
```

Your Java project structure should look like:
```
your-java-project/
├── src/main/resources/db/migration/
│   ├── V1.0.0__Initial_schema.sql  # Your existing migrations
│   ├── V1.1.0__Add_pgvector_extension.sql
│   ├── V1.2.0__Enhance_location_table.sql
│   ├── V1.3.0__Enhance_event_table.sql
│   ├── V1.4.0__Add_vector_search_functions.sql
│   └── V1.5.0__Create_enhanced_views.sql
```

### 2. Update Your Java Dependencies

Add pgvector support to your `pom.xml` or `build.gradle`:

**Maven (pom.xml):**
```xml
<dependency>
    <groupId>com.pgvector</groupId>
    <artifactId>pgvector</artifactId>
    <version>0.1.4</version>
</dependency>
```

**Gradle (build.gradle):**
```groovy
implementation 'com.pgvector:pgvector:0.1.4'
```

### 3. Update Your Application Configuration

**application.yml:**
```yaml
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/your_database
    username: postgres
    password: postgres
  flyway:
    enabled: true
    baseline-on-migrate: true
    locations: classpath:db/migration
    schemas: public
```

**application.properties:**
```properties
spring.datasource.url=jdbc:postgresql://localhost:5432/your_database
spring.datasource.username=postgres
spring.datasource.password=postgres
spring.flyway.enabled=true
spring.flyway.baseline-on-migrate=true
spring.flyway.locations=classpath:db/migration
spring.flyway.schemas=public
```

### 4. Create Java Entities for Enhanced Fields

Update your existing `Event` entity:

```java
@Entity
@Table(name = "event")
public class Event {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "event_id")
    private Long eventId;
    
    // Your existing fields...
    private String title;
    private String description;
    private BigDecimal price;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "location_id")
    private Location location;
    
    // New AI-enhanced fields
    @Column(name = "duration_min")
    private Integer durationMin;
    
    @Column(name = "indoor")
    private Boolean indoor = false;
    
    @Column(name = "kid_friendly")
    private Boolean kidFriendly = false;
    
    @Column(name = "website")
    private String website;
    
    @Column(name = "phone")
    private String phone;
    
    @Column(name = "rating")
    private Double rating = 0.0;
    
    @Column(name = "review_count")
    private Integer reviewCount = 0;
    
    @Column(name = "is_ai_recommended")
    private Boolean isAiRecommended = false;
    
    @Column(name = "ai_score")
    private BigDecimal aiScore;
    
    @Column(name = "popularity")
    private Integer popularity;
    
    // Vector embedding (stored as JSON string in Java)
    @Column(name = "embedding", columnDefinition = "vector(384)")
    private String embedding;
    
    @Type(JsonType.class)
    @Column(name = "metadata", columnDefinition = "jsonb")
    private Map<String, Object> metadata = new HashMap<>();
    
    // Getters and setters...
}
```

Update your `Location` entity:

```java
@Entity
@Table(name = "location")
public class Location {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "location_id")
    private Long locationId;
    
    // Your existing fields...
    private String name;
    private String address;
    private String city;
    private String state;
    private String country;
    
    // New coordinate fields for AI search
    @Column(name = "lat")
    private Double lat;
    
    @Column(name = "lon")  
    private Double lon;
    
    // Getters and setters...
}
```

### 5. Create Repository Methods for AI Features

```java
@Repository
public interface EventRepository extends JpaRepository<Event, Long> {
    
    // Find events with embeddings (ready for AI search)
    @Query("SELECT e FROM Event e WHERE e.embedding IS NOT NULL")
    List<Event> findEventsWithEmbeddings();
    
    // Find AI recommended events
    @Query("SELECT e FROM Event e WHERE e.isAiRecommended = true")
    List<Event> findAiRecommendedEvents();
    
    // Find events needing embeddings
    @Query("SELECT e FROM Event e WHERE e.embedding IS NULL")
    List<Event> findEventsNeedingEmbeddings();
    
    // Find events by city with embeddings
    @Query("SELECT e FROM Event e JOIN e.location l WHERE l.city = :city AND e.embedding IS NOT NULL")
    List<Event> findEventsByCityWithEmbeddings(@Param("city") String city);
    
    // Custom native query for vector search (when called from Java)
    @Query(value = """
        SELECT * FROM search_events_by_similarity(
            :embedding::vector, :threshold, :maxResults, :city, :maxPrice, :indoor, :categories, :minDuration, :maxDuration
        )
        """, nativeQuery = true)
    List<Object[]> searchByVectorSimilarity(
        @Param("embedding") String embedding,
        @Param("threshold") Double threshold,
        @Param("maxResults") Integer maxResults,
        @Param("city") String city,
        @Param("maxPrice") Double maxPrice,
        @Param("indoor") Boolean indoor,
        @Param("categories") String[] categories,
        @Param("minDuration") Integer minDuration,
        @Param("maxDuration") Integer maxDuration
    );
}
```

### 6. Create AI Integration Service

```java
@Service
@Transactional
public class AiIntegrationService {
    
    @Autowired
    private EventRepository eventRepository;
    
    /**
     * Mark events for AI embedding refresh when content changes
     */
    public void refreshEventEmbeddings(Long eventId) {
        Event event = eventRepository.findById(eventId).orElse(null);
        if (event != null) {
            // Clear embedding to trigger refresh by AI service
            event.setEmbedding(null);
            eventRepository.save(event);
        }
    }
    
    /**
     * Get AI integration statistics
     */
    public Map<String, Object> getAiStats() {
        Map<String, Object> stats = new HashMap<>();
        
        long totalEvents = eventRepository.count();
        long eventsWithEmbeddings = eventRepository.findEventsWithEmbeddings().size();
        long aiRecommendedEvents = eventRepository.findAiRecommendedEvents().size();
        
        stats.put("totalEvents", totalEvents);
        stats.put("eventsWithEmbeddings", eventsWithEmbeddings);
        stats.put("aiRecommendedEvents", aiRecommendedEvents);
        stats.put("embeddingCoverage", totalEvents > 0 ? (double) eventsWithEmbeddings / totalEvents * 100 : 0);
        
        return stats;
    }
    
    /**
     * Prepare events for AI processing
     */
    @Scheduled(fixedRate = 300000) // Every 5 minutes
    public void scheduleEmbeddingRefresh() {
        List<Event> eventsNeedingEmbeddings = eventRepository.findEventsNeedingEmbeddings();
        
        if (!eventsNeedingEmbeddings.isEmpty()) {
            log.info("Found {} events needing AI embeddings", eventsNeedingEmbeddings.size());
            // Could trigger AI service processing here
        }
    }
}
```

## Running the Migration

### 1. Run Flyway Migration

**Option A: Via Maven**
```bash
mvn flyway:migrate
```

**Option B: Via Gradle**
```bash
./gradlew flywayMigrate
```

**Option C: Automatic on Spring Boot startup**
```bash
# Migrations run automatically when you start your Spring Boot app
mvn spring-boot:run
```

### 2. Verify Migration Success

Check that the migrations completed successfully:

```sql
-- Check Flyway migration history
SELECT * FROM flyway_schema_history ORDER BY installed_on DESC;

-- Verify pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check new columns exist
\d event
\d location

-- Test vector search function
SELECT COUNT(*) FROM search_events_by_similarity('[0.1,0.2,0.3]'::vector, 0.1, 10, null, null, null, null, null, null);
```

### 3. Initialize AI Embeddings

After successful migration, populate embeddings:

```bash
# From the AI Orchestrator directory
python populate_vector_store.py
```

## Integration Testing

### Java Side Testing

```java
@SpringBootTest
@TestPropertySource(properties = {
    "spring.flyway.clean-disabled=false"
})
class AiIntegrationTest {
    
    @Autowired
    private EventRepository eventRepository;
    
    @Autowired
    private AiIntegrationService aiIntegrationService;
    
    @Test
    void testEnhancedEventFields() {
        Event event = new Event();
        event.setTitle("Test Event");
        event.setDurationMin(120);
        event.setIndoor(true);
        event.setKidFriendly(false);
        event.setRating(4.5);
        
        Event saved = eventRepository.save(event);
        
        assertThat(saved.getDurationMin()).isEqualTo(120);
        assertThat(saved.getIndoor()).isTrue();
        assertThat(saved.getRating()).isEqualTo(4.5);
    }
    
    @Test
    void testAiStats() {
        Map<String, Object> stats = aiIntegrationService.getAiStats();
        
        assertThat(stats).containsKey("totalEvents");
        assertThat(stats).containsKey("embeddingCoverage");
    }
}
```

### Python Side Testing

```bash
# Test that Python can read Java data
python -c "
from server.tools.vector_store import get_vector_store
vs = get_vector_store()
stats = vs.get_stats()
print('Java Events with embeddings:', stats.get('postgresql_events_with_embeddings', 0))
"
```

## Rollback Strategy

If you need to rollback the migrations:

### 1. Flyway Rollback (if using Flyway Teams)
```bash
mvn flyway:undo
```

### 2. Manual Rollback
```sql
-- Remove AI enhancements (in reverse order)
DROP VIEW IF EXISTS ai_orchestrator_stats;
DROP VIEW IF EXISTS date_ideas;
DROP VIEW IF EXISTS enhanced_events_view;
DROP FUNCTION IF EXISTS search_date_ideas_by_similarity;
DROP FUNCTION IF EXISTS search_events_by_similarity;
DROP FUNCTION IF EXISTS update_event_modified_time;

-- Remove columns from event table
ALTER TABLE event 
DROP COLUMN IF EXISTS metadata,
DROP COLUMN IF EXISTS embedding,
DROP COLUMN IF EXISTS review_count,
DROP COLUMN IF EXISTS rating,
DROP COLUMN IF EXISTS phone,
DROP COLUMN IF EXISTS website,
DROP COLUMN IF EXISTS kid_friendly,
DROP COLUMN IF EXISTS indoor,
DROP COLUMN IF EXISTS duration_min;

-- Remove columns from location table
ALTER TABLE location 
DROP COLUMN IF EXISTS lon,
DROP COLUMN IF EXISTS lat;

-- Remove extension (requires superuser)
DROP EXTENSION IF EXISTS vector;
```

## Monitoring and Maintenance

### 1. Monitor Embedding Coverage
```java
@RestController
public class AiMonitoringController {
    
    @Autowired
    private AiIntegrationService aiIntegrationService;
    
    @GetMapping("/admin/ai/stats")
    public ResponseEntity<Map<String, Object>> getAiStats() {
        return ResponseEntity.ok(aiIntegrationService.getAiStats());
    }
}
```

### 2. Database Health Checks
```sql
-- Check embedding coverage
SELECT * FROM ai_orchestrator_stats;

-- Find events modified recently without embeddings
SELECT event_id, title, modified_time 
FROM event 
WHERE modified_time > NOW() - INTERVAL '1 day' 
AND embedding IS NULL;
```

### 3. Performance Monitoring
```sql
-- Monitor vector search performance
EXPLAIN ANALYZE 
SELECT * FROM search_events_by_similarity('[0.1,0.2,...]'::vector, 0.5, 10, 'Ottawa', null, null, null, null, null);
```

This Flyway integration ensures that your database schema changes are version-controlled, repeatable, and safely deployed alongside your Java application updates.