-- Database initialization and schema for AI Orchestrator
-- This script sets up the PostgreSQL database with pgvector extension
-- Compatible with existing Java schema while adding vector capabilities

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- ===== EXISTING JAVA SCHEMA TABLES =====
-- These tables match your Java application schema

-- Table for event categories (e.g., "Romantic", "Adventure")
CREATE TABLE IF NOT EXISTS event_category (
    category_id SERIAL PRIMARY KEY,         -- Auto-incremented Category ID
    name VARCHAR(255) NOT NULL               -- Category Name (e.g., "Romantic", "Adventure")
);

-- Location table to store locations
CREATE TABLE IF NOT EXISTS location (
    location_id SERIAL PRIMARY KEY,         -- Auto-incremented Location ID
    name VARCHAR(255),                      -- Location Name
    address VARCHAR(255),                   -- Full Address (optional)
    city VARCHAR(255),                      -- City (optional)
    state VARCHAR(255),                     -- State (optional)
    country VARCHAR(255),                   -- Country (optional)
    lat REAL,                              -- Latitude (added for vector search)
    lon REAL                               -- Longitude (added for vector search)
);

-- Create the Event table (enhanced with vector fields)
CREATE TABLE IF NOT EXISTS event (
    event_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2),
    location_id INTEGER,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_ai_recommended BOOLEAN DEFAULT FALSE,
    ai_score DECIMAL(5, 2),
    popularity INTEGER,
    
    -- Enhanced fields for AI vector search
    duration_min INTEGER,                   -- Duration in minutes
    indoor BOOLEAN,                         -- Indoor/outdoor flag
    kid_friendly BOOLEAN,                   -- Kid-friendly flag
    website TEXT,                          -- Website URL
    phone TEXT,                            -- Phone number
    rating REAL,                           -- Rating (1-5)
    review_count INTEGER,                  -- Number of reviews
    
    -- Vector embedding for semantic search (384 dimensions for all-MiniLM-L6-v2)
    embedding vector(384),
    
    -- Additional metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT fk_location FOREIGN KEY (location_id) REFERENCES location(location_id)
);

-- Many-to-many relationship between events and categories
CREATE TABLE IF NOT EXISTS event_category_link (
    event_id INTEGER,                       -- Foreign Key to event
    category_id INTEGER,                    -- Foreign Key to event_category
    PRIMARY KEY (event_id, category_id),   -- Composite primary key
    CONSTRAINT fk_event FOREIGN KEY (event_id) REFERENCES event(event_id),
    CONSTRAINT fk_category FOREIGN KEY (category_id) REFERENCES event_category(category_id)
);

-- Table to store related events (many-to-many relationship)
CREATE TABLE IF NOT EXISTS related_event (
    event_id INTEGER,                       -- Foreign Key to event
    related_event_id INTEGER,               -- Foreign Key to another event
    PRIMARY KEY (event_id, related_event_id), -- Composite primary key
    CONSTRAINT fk_event_1 FOREIGN KEY (event_id) REFERENCES event(event_id),
    CONSTRAINT fk_event_2 FOREIGN KEY (related_event_id) REFERENCES event(event_id)
);

-- Table to store AI recommendations (optional)
CREATE TABLE IF NOT EXISTS ai_recommendation (
    ai_recommendation_id SERIAL PRIMARY KEY,   -- Auto-incremented Recommendation ID
    event_id INTEGER,                           -- Foreign Key to event
    recommendation_text TEXT,                   -- AI-generated recommendation text
    recommendation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Timestamp for recommendation
    CONSTRAINT fk_event_ai FOREIGN KEY (event_id) REFERENCES event(event_id)
);

-- ===== COMPATIBILITY VIEW FOR AI ORCHESTRATOR =====
-- This view maps the Java schema to the expected AI Orchestrator format
-- Allows the Python vector store to work with existing Java data

CREATE OR REPLACE VIEW date_ideas AS
SELECT 
    'event_' || e.event_id::text as id,
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
    LOWER(REPLACE(COALESCE(l.city, ''), ' ', '_')) as city_id,
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
    COALESCE(e.website, '') as website,
    COALESCE(e.phone, '') as phone,
    '{}' as open_hours_json,
    COALESCE(e.rating, 0.0) as rating,
    COALESCE(e.review_count, 0) as review_count,
    
    -- Venue/Business mapping (using location as venue)
    'venue_' || l.location_id::text as venue_id,
    l.name as venue_name,
    '' as business_id,
    '' as business_name,
    l.address,
    '' as neighborhood,
    
    -- Vector embedding
    e.embedding,
    
    -- Metadata
    e.created_time as created_at,
    e.modified_time as updated_at,
    e.metadata
FROM event e
LEFT JOIN location l ON e.location_id = l.location_id;

-- Indexes for efficient querying on the enhanced event table
CREATE INDEX IF NOT EXISTS idx_event_location ON event (location_id);
CREATE INDEX IF NOT EXISTS idx_event_price ON event (price);
CREATE INDEX IF NOT EXISTS idx_event_duration ON event (duration_min);
CREATE INDEX IF NOT EXISTS idx_event_indoor ON event (indoor);
CREATE INDEX IF NOT EXISTS idx_event_rating ON event (rating DESC);
CREATE INDEX IF NOT EXISTS idx_event_ai_recommended ON event (is_ai_recommended);
CREATE INDEX IF NOT EXISTS idx_event_popularity ON event (popularity DESC);

-- Indexes for location table
CREATE INDEX IF NOT EXISTS idx_location_city ON location (city);
CREATE INDEX IF NOT EXISTS idx_location_coords ON location (lat, lon);

-- Indexes for category relationships
CREATE INDEX IF NOT EXISTS idx_event_category_link_event ON event_category_link (event_id);
CREATE INDEX IF NOT EXISTS idx_event_category_link_category ON event_category_link (category_id);
CREATE INDEX IF NOT EXISTS idx_event_category_name ON event_category (name);

-- Vector similarity search index using HNSW (Hierarchical Navigable Small World)
-- This enables fast approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS idx_event_embedding ON event 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- Compatibility indexes for the date_ideas view
CREATE INDEX IF NOT EXISTS idx_date_ideas_view_city ON event ((
    (SELECT city FROM location l WHERE l.location_id = event.location_id)
));

-- Trigger to update modified_time timestamp
CREATE OR REPLACE FUNCTION update_modified_time_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_time = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_event_modified_time ON event;
CREATE TRIGGER update_event_modified_time 
    BEFORE UPDATE ON event 
    FOR EACH ROW 
    EXECUTE FUNCTION update_modified_time_column();

-- Function to search events by vector similarity (compatible with Java schema)
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

-- Legacy compatibility function (maps to date_ideas format expected by Python)
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

-- Enhanced view for easier querying with computed fields
CREATE OR REPLACE VIEW enhanced_events_view AS
SELECT 
    e.event_id,
    'event_' || e.event_id::text as ai_id,
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
    CASE 
        WHEN e.price <= 25 THEN '$'
        WHEN e.price <= 75 THEN '$$'
        ELSE '$$$'
    END as price_display,
    COALESCE(e.duration_min, 60) as duration_min,
    CASE 
        WHEN COALESCE(e.duration_min, 60) < 60 THEN COALESCE(e.duration_min, 60) || ' minutes'
        ELSE (COALESCE(e.duration_min, 60) / 60) || ' hours'
    END as duration_display,
    COALESCE(e.indoor, false) as indoor,
    COALESCE(e.kid_friendly, false) as kid_friendly,
    COALESCE(e.website, '') as website,
    COALESCE(e.phone, '') as phone,
    COALESCE(e.rating, 0.0) as rating,
    COALESCE(e.review_count, 0) as review_count,
    l.name as venue_name,
    l.address,
    e.is_ai_recommended,
    e.ai_score,
    COALESCE(e.popularity, 0) as popularity,
    e.created_time,
    e.modified_time,
    e.embedding IS NOT NULL as has_embedding
FROM event e
LEFT JOIN location l ON e.location_id = l.location_id;

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON date_ideas TO your_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_app_user;