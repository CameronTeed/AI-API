-- Flyway Migration: Add event expiry and cleanup functionality
-- Migration version: V8_1_0
-- Description: Add event expiry dates and automatic cleanup system
-- Author: AI Orchestrator Enhancement
-- Date: 2025-09-27

-- Add expiry-related columns to the event table
ALTER TABLE event 
ADD COLUMN IF NOT EXISTS expiry_date TIMESTAMP,
ADD COLUMN IF NOT EXISTS auto_cleanup_enabled BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS cleanup_reason TEXT;

-- Create index for efficient expiry queries
CREATE INDEX IF NOT EXISTS idx_event_expiry_date ON event (expiry_date) WHERE expiry_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_event_active ON event (is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_event_auto_cleanup ON event (auto_cleanup_enabled, expiry_date) WHERE auto_cleanup_enabled = true;

-- Create audit table for tracking cleanup operations
CREATE TABLE IF NOT EXISTS event_cleanup_audit (
    audit_id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    event_title VARCHAR(255),
    cleanup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cleanup_type VARCHAR(50) NOT NULL, -- 'soft_delete', 'hard_delete', 'archive'
    cleanup_reason TEXT,
    restored_date TIMESTAMP,
    created_by VARCHAR(255) DEFAULT 'system'
);

-- Index for audit queries
CREATE INDEX IF NOT EXISTS idx_cleanup_audit_event ON event_cleanup_audit (event_id);
CREATE INDEX IF NOT EXISTS idx_cleanup_audit_date ON event_cleanup_audit (cleanup_date);
CREATE INDEX IF NOT EXISTS idx_cleanup_audit_type ON event_cleanup_audit (cleanup_type);

-- Function to check if an event is expired
CREATE OR REPLACE FUNCTION is_event_expired(expiry_date TIMESTAMP)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN expiry_date IS NOT NULL AND expiry_date < NOW();
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to soft delete expired events
CREATE OR REPLACE FUNCTION soft_delete_expired_events()
RETURNS TABLE (
    deleted_count INTEGER,
    event_ids INTEGER[]
) AS $$
DECLARE
    deleted_ids INTEGER[];
    count_deleted INTEGER;
BEGIN
    -- Get IDs of events to be soft deleted
    SELECT ARRAY(
        SELECT e.event_id
        FROM event e
        WHERE e.is_active = true
          AND e.auto_cleanup_enabled = true
          AND is_event_expired(e.expiry_date)
    ) INTO deleted_ids;
    
    -- Soft delete expired events
    UPDATE event 
    SET is_active = false,
        cleanup_reason = 'Expired on ' || expiry_date::date
    WHERE event_id = ANY(deleted_ids);
    
    GET DIAGNOSTICS count_deleted = ROW_COUNT;
    
    -- Log to audit table
    INSERT INTO event_cleanup_audit (event_id, event_title, cleanup_type, cleanup_reason)
    SELECT e.event_id, e.title, 'soft_delete', 'Auto cleanup - expired'
    FROM event e
    WHERE e.event_id = ANY(deleted_ids);
    
    RETURN QUERY SELECT count_deleted, deleted_ids;
END;
$$ LANGUAGE plpgsql;

-- Function to restore soft deleted events
CREATE OR REPLACE FUNCTION restore_event(target_event_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    event_exists BOOLEAN := false;
BEGIN
    -- Check if event exists and is soft deleted
    SELECT EXISTS(
        SELECT 1 FROM event 
        WHERE event_id = target_event_id AND is_active = false
    ) INTO event_exists;
    
    IF event_exists THEN
        -- Restore the event
        UPDATE event 
        SET is_active = true,
            cleanup_reason = NULL,
            modified_time = NOW()
        WHERE event_id = target_event_id;
        
        -- Log restoration
        UPDATE event_cleanup_audit
        SET restored_date = NOW()
        WHERE event_id = target_event_id AND restored_date IS NULL;
        
        RETURN true;
    END IF;
    
    RETURN false;
END;
$$ LANGUAGE plpgsql;

-- Function to hard delete old soft-deleted events (for cleanup)
CREATE OR REPLACE FUNCTION hard_delete_old_events(days_old INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
    cutoff_date TIMESTAMP;
BEGIN
    cutoff_date := NOW() - INTERVAL '1 day' * days_old;
    
    -- Log events to be hard deleted
    INSERT INTO event_cleanup_audit (event_id, event_title, cleanup_type, cleanup_reason)
    SELECT e.event_id, e.title, 'hard_delete', 'Permanent cleanup after ' || days_old || ' days'
    FROM event e
    WHERE e.is_active = false
      AND e.modified_time < cutoff_date;
    
    -- Hard delete events
    DELETE FROM event
    WHERE is_active = false
      AND modified_time < cutoff_date;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get cleanup statistics
CREATE OR REPLACE FUNCTION get_cleanup_statistics()
RETURNS TABLE (
    total_events INTEGER,
    active_events INTEGER,
    expired_events INTEGER,
    soft_deleted_events INTEGER,
    events_expiring_soon INTEGER -- within 7 days
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*)::INTEGER FROM event) as total_events,
        (SELECT COUNT(*)::INTEGER FROM event WHERE is_active = true) as active_events,
        (SELECT COUNT(*)::INTEGER FROM event WHERE is_active = true AND is_event_expired(expiry_date)) as expired_events,
        (SELECT COUNT(*)::INTEGER FROM event WHERE is_active = false) as soft_deleted_events,
        (SELECT COUNT(*)::INTEGER FROM event 
         WHERE is_active = true 
           AND expiry_date IS NOT NULL 
           AND expiry_date > NOW() 
           AND expiry_date <= NOW() + INTERVAL '7 days') as events_expiring_soon;
END;
$$ LANGUAGE plpgsql;

-- Update the existing views to respect expiry and active status
DROP VIEW IF EXISTS date_ideas;
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
    
    -- Metadata including expiry information
    e.created_time as created_at,
    e.modified_time as updated_at,
    e.expiry_date,
    is_event_expired(e.expiry_date) as is_expired,
    e.is_active,
    e.metadata
FROM event e
LEFT JOIN location l ON e.location_id = l.location_id
WHERE e.is_active = true  -- Only show active events
  AND (e.expiry_date IS NULL OR e.expiry_date > NOW()); -- Only show non-expired events

-- Update search functions to respect expiry
CREATE OR REPLACE FUNCTION search_events_by_similarity(
    query_embedding vector(384),
    similarity_threshold REAL DEFAULT 0.5,
    max_results INTEGER DEFAULT 10,
    filter_city TEXT DEFAULT NULL,
    filter_max_price REAL DEFAULT NULL,
    filter_indoor BOOLEAN DEFAULT NULL,
    filter_categories TEXT[] DEFAULT NULL,
    filter_min_duration INTEGER DEFAULT NULL,
    filter_max_duration INTEGER DEFAULT NULL,
    include_expired BOOLEAN DEFAULT false
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
    popularity INTEGER,
    expiry_date TIMESTAMP,
    is_expired BOOLEAN
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
        COALESCE(e.popularity, 0) as popularity,
        e.expiry_date,
        is_event_expired(e.expiry_date) as is_expired
    FROM event e
    LEFT JOIN location l ON e.location_id = l.location_id
    WHERE 
        e.embedding IS NOT NULL
        AND e.is_active = true
        AND (include_expired = true OR e.expiry_date IS NULL OR e.expiry_date > NOW())
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

-- Add comments for documentation
COMMENT ON COLUMN event.expiry_date IS 'Optional expiry date for the event';
COMMENT ON COLUMN event.auto_cleanup_enabled IS 'Whether this event should be automatically cleaned up when expired';
COMMENT ON COLUMN event.is_active IS 'Soft delete flag - false means event is deleted but preserved';
COMMENT ON COLUMN event.cleanup_reason IS 'Reason why the event was marked as inactive';
COMMENT ON TABLE event_cleanup_audit IS 'Audit log for event cleanup operations';

-- Grant necessary permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON event_cleanup_audit TO your_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_app_user;