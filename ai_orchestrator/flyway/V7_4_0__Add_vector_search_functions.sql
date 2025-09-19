-- Flyway Migration: Add vector search functions and views
-- Migration version: V1.4.0
-- Description: Create functions and views for AI vector search integration
-- Author: AI Orchestrator Integration
-- Date: 2025-09-13

-- Function to automatically update modified_time when event is updated
CREATE OR REPLACE FUNCTION update_event_modified_time()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_time = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update modified_time
DROP TRIGGER IF EXISTS trigger_update_event_modified_time ON event;
CREATE TRIGGER trigger_update_event_modified_time
    BEFORE UPDATE ON event
    FOR EACH ROW
    EXECUTE FUNCTION update_event_modified_time();

-- Function for vector similarity search compatible with Java application
CREATE OR REPLACE FUNCTION search_events_by_similarity(
    query_embedding vector(384),
    similarity_threshold REAL DEFAULT 0.5,
    max_results INTEGER DEFAULT 10,
    filter_city TEXT DEFAULT NULL,
    filter_max_price REAL DEFAULT NULL,
    filter_indoor BOOLEAN DEFAULT NULL,
    filter_categories TEXT[] DEFAULT NULL,
    filter_min_duration INTEGER DEFAULT NULL,
    filter_max_duration INTEGER DEFAULT NULL
)
RETURNS TABLE (
    event_id INTEGER,
    title VARCHAR(255),
    description TEXT,
    categories TEXT[],
    city TEXT,
    lat REAL,
    lon REAL,
    price DECIMAL(10,2),
    price_tier INTEGER,
    duration_min INTEGER,
    indoor BOOLEAN,
    kid_friendly BOOLEAN,
    website TEXT,
    phone TEXT,
    rating REAL,
    review_count INTEGER,
    venue_name TEXT,
    address TEXT,
    similarity_score REAL,
    is_ai_recommended BOOLEAN,
    ai_score DECIMAL(5,2),
    popularity INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.event_id,
        e.title,
        e.description,
        COALESCE(
            ARRAY(
                SELECT ec.name 
                FROM event_category_link ecl 
                JOIN event_category ec ON ecl.category_id = ec.category_id 
                WHERE ecl.event_id = e.event_id
            ), 
            ARRAY[]::VARCHAR[]
        ) as categories,
        l.city,
        l.lat,
        l.lon,
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
        (1 - (e.embedding <=> query_embedding)) AS similarity_score,
        e.is_ai_recommended,
        e.ai_score,
        COALESCE(e.popularity, 0) as popularity
    FROM event e
    LEFT JOIN location l ON e.location_id = l.location_id
    WHERE 
        e.embedding IS NOT NULL
        AND (1 - (e.embedding <=> query_embedding)) >= similarity_threshold
        AND (filter_city IS NULL OR l.city ILIKE '%' || filter_city || '%')
        AND (filter_max_price IS NULL OR e.price <= filter_max_price)
        AND (filter_indoor IS NULL OR COALESCE(e.indoor, false) = filter_indoor)
        AND (filter_categories IS NULL OR 
             EXISTS (
                 SELECT 1 FROM event_category_link ecl 
                 JOIN event_category ec ON ecl.category_id = ec.category_id 
                 WHERE ecl.event_id = e.event_id 
                 AND ec.name = ANY(filter_categories)
             ))
        AND (filter_min_duration IS NULL OR COALESCE(e.duration_min, 60) >= filter_min_duration)
        AND (filter_max_duration IS NULL OR COALESCE(e.duration_min, 60) <= filter_max_duration)
    ORDER BY similarity_score DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Legacy compatibility function for AI Orchestrator Python code
CREATE OR REPLACE FUNCTION search_date_ideas_by_similarity(
    query_embedding vector(384),
    similarity_threshold REAL DEFAULT 0.5,
    max_results INTEGER DEFAULT 10,
    filter_city TEXT DEFAULT NULL,
    filter_max_price_tier INTEGER DEFAULT NULL,
    filter_indoor BOOLEAN DEFAULT NULL,
    filter_categories TEXT[] DEFAULT NULL,
    filter_min_duration INTEGER DEFAULT NULL,
    filter_max_duration INTEGER DEFAULT NULL
)
RETURNS TABLE (
    id TEXT,
    title TEXT,
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
    venue_name TEXT,
    business_name TEXT,
    address TEXT,
    similarity_score REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        'event_' || e.event_id::text as id,
        e.title::text,
        e.description,
        COALESCE(
            ARRAY(
                SELECT ec.name 
                FROM event_category_link ecl 
                JOIN event_category ec ON ecl.category_id = ec.category_id 
                WHERE ecl.event_id = e.event_id
            ), 
            ARRAY[]::VARCHAR[]
        ) as categories,
        l.city::text,
        COALESCE(l.lat, 0.0) as lat,
        COALESCE(l.lon, 0.0) as lon,
        CASE 
            WHEN e.price <= 25 THEN 1
            WHEN e.price <= 75 THEN 2
            ELSE 3
        END as price_tier,
        COALESCE(e.duration_min, 60) as duration_min,
        COALESCE(e.indoor, false) as indoor,
        COALESCE(e.kid_friendly, false) as kid_friendly,
        COALESCE(e.website, '')::text as website,
        COALESCE(e.phone, '')::text as phone,
        COALESCE(e.rating, 0.0) as rating,
        COALESCE(e.review_count, 0) as review_count,
        l.name::text as venue_name,
        ''::text as business_name,
        l.address::text,
        (1 - (e.embedding <=> query_embedding)) AS similarity_score
    FROM event e
    LEFT JOIN location l ON e.location_id = l.location_id
    WHERE 
        e.embedding IS NOT NULL
        AND (1 - (e.embedding <=> query_embedding)) >= similarity_threshold
        AND (filter_city IS NULL OR l.city ILIKE '%' || filter_city || '%')
        AND (filter_max_price_tier IS NULL OR 
             CASE 
                 WHEN e.price <= 25 THEN 1
                 WHEN e.price <= 75 THEN 2
                 ELSE 3
             END <= filter_max_price_tier)
        AND (filter_indoor IS NULL OR COALESCE(e.indoor, false) = filter_indoor)
        AND (filter_categories IS NULL OR 
             EXISTS (
                 SELECT 1 FROM event_category_link ecl 
                 JOIN event_category ec ON ecl.category_id = ec.category_id 
                 WHERE ecl.event_id = e.event_id 
                 AND ec.name = ANY(filter_categories)
             ))
        AND (filter_min_duration IS NULL OR COALESCE(e.duration_min, 60) >= filter_min_duration)
        AND (filter_max_duration IS NULL OR COALESCE(e.duration_min, 60) <= filter_max_duration)
    ORDER BY similarity_score DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Add function comments
COMMENT ON FUNCTION search_events_by_similarity IS 'AI Orchestrator: Search events using vector similarity with Java schema compatibility';
COMMENT ON FUNCTION search_date_ideas_by_similarity IS 'AI Orchestrator: Legacy compatibility function for Python AI Orchestrator';
COMMENT ON FUNCTION update_event_modified_time IS 'AI Orchestrator: Automatically update modified_time on event changes';