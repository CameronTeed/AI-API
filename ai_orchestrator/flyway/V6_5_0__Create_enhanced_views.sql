-- Flyway Migration: Create enhanced views for AI integration
-- Migration version: V1.5.0
-- Description: Create views that provide enhanced data access for both Java and AI applications
-- Author: AI Orchestrator Integration
-- Date: 2025-09-13

-- Enhanced events view with computed fields and AI-friendly format
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
    e.embedding IS NOT NULL as has_embedding,
    -- Computed fields for Java application convenience
    CASE 
        WHEN e.embedding IS NOT NULL THEN 'READY'
        ELSE 'PENDING'
    END as ai_status,
    -- Category count for filtering
    (
        SELECT COUNT(*) 
        FROM event_category_link ecl 
        WHERE ecl.event_id = e.event_id
    ) as category_count
FROM event e
LEFT JOIN location l ON e.location_id = l.location_id;

-- Compatibility view that maps Java schema to AI Orchestrator expected format
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

-- AI statistics view for monitoring and analytics
CREATE OR REPLACE VIEW ai_orchestrator_stats AS
SELECT 
    'events' as entity_type,
    COUNT(*) as total_count,
    COUNT(embedding) as with_embeddings,
    COUNT(*) - COUNT(embedding) as missing_embeddings,
    ROUND(COUNT(embedding) * 100.0 / COUNT(*), 2) as embedding_coverage_percent,
    MIN(created_time) as oldest_event,
    MAX(modified_time) as latest_update
FROM event
UNION ALL
SELECT 
    'locations' as entity_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN lat IS NOT NULL AND lon IS NOT NULL THEN 1 END) as with_embeddings,
    COUNT(CASE WHEN lat IS NULL OR lon IS NULL THEN 1 END) as missing_embeddings,
    ROUND(COUNT(CASE WHEN lat IS NOT NULL AND lon IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as embedding_coverage_percent,
    NULL as oldest_event,
    NULL as latest_update
FROM location
UNION ALL
SELECT 
    'categories' as entity_type,
    COUNT(*) as total_count,
    0 as with_embeddings,
    0 as missing_embeddings,
    100.0 as embedding_coverage_percent,
    NULL as oldest_event,
    NULL as latest_update
FROM event_category;

-- Add view comments for documentation
COMMENT ON VIEW enhanced_events_view IS 'AI Orchestrator: Enhanced view with computed fields for both Java and AI applications';
COMMENT ON VIEW date_ideas IS 'AI Orchestrator: Compatibility view mapping Java schema to AI Orchestrator expected format';
COMMENT ON VIEW ai_orchestrator_stats IS 'AI Orchestrator: Statistics view for monitoring embedding coverage and data health';