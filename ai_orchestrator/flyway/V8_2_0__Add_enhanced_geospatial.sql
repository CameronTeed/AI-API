-- Flyway Migration: Add PostGIS geospatial capabilities
-- Migration version: V8_2_0
-- Description: Enable PostGIS and add enhanced geospatial search capabilities
-- Author: AI Orchestrator Enhancement
-- Date: 2025-09-27

-- Enable PostGIS extension for advanced geospatial operations
CREATE EXTENSION IF NOT EXISTS postgis;

-- Add geometry columns to the location table
ALTER TABLE location 
ADD COLUMN IF NOT EXISTS geom GEOMETRY(POINT, 4326),
ADD COLUMN IF NOT EXISTS geom_mercator GEOMETRY(POINT, 3857); -- Web Mercator for better distance calculations

-- Create function to update geometry columns from lat/lon
CREATE OR REPLACE FUNCTION update_location_geometry()
RETURNS TRIGGER AS $$
BEGIN
    -- Update WGS84 geometry (SRID 4326)
    IF NEW.lat IS NOT NULL AND NEW.lon IS NOT NULL THEN
        NEW.geom = ST_SetSRID(ST_MakePoint(NEW.lon, NEW.lat), 4326);
        -- Update Web Mercator geometry for distance calculations
        NEW.geom_mercator = ST_Transform(NEW.geom, 3857);
    ELSE
        NEW.geom = NULL;
        NEW.geom_mercator = NULL;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update geometry when lat/lon changes
DROP TRIGGER IF EXISTS trigger_update_location_geometry ON location;
CREATE TRIGGER trigger_update_location_geometry
    BEFORE INSERT OR UPDATE OF lat, lon ON location
    FOR EACH ROW
    EXECUTE FUNCTION update_location_geometry();

-- Update existing records with geometry data
UPDATE location 
SET geom = ST_SetSRID(ST_MakePoint(lon, lat), 4326),
    geom_mercator = ST_Transform(ST_SetSRID(ST_MakePoint(lon, lat), 4326), 3857)
WHERE lat IS NOT NULL AND lon IS NOT NULL AND geom IS NULL;

-- Create spatial indexes
CREATE INDEX IF NOT EXISTS idx_location_geom ON location USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_location_geom_mercator ON location USING GIST (geom_mercator);

-- Create areas/neighborhoods table for named geographic regions
CREATE TABLE IF NOT EXISTS geographic_area (
    area_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    area_type VARCHAR(50) NOT NULL, -- 'neighborhood', 'district', 'city', 'county', 'custom'
    city VARCHAR(255),
    state VARCHAR(255),
    country VARCHAR(255),
    geom GEOMETRY(POLYGON, 4326), -- Area boundary
    center_point GEOMETRY(POINT, 4326), -- Center of the area
    radius_meters REAL, -- For circular areas
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for geographic areas
CREATE INDEX IF NOT EXISTS idx_geographic_area_geom ON geographic_area USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_geographic_area_center ON geographic_area USING GIST (center_point);
CREATE INDEX IF NOT EXISTS idx_geographic_area_name ON geographic_area (name);
CREATE INDEX IF NOT EXISTS idx_geographic_area_type ON geographic_area (area_type);
CREATE INDEX IF NOT EXISTS idx_geographic_area_city ON geographic_area (city);

-- Create table to link events to geographic areas
CREATE TABLE IF NOT EXISTS event_geographic_area (
    event_id INTEGER NOT NULL,
    area_id INTEGER NOT NULL,
    PRIMARY KEY (event_id, area_id),
    CONSTRAINT fk_event_area_event FOREIGN KEY (event_id) REFERENCES event(event_id) ON DELETE CASCADE,
    CONSTRAINT fk_event_area_area FOREIGN KEY (area_id) REFERENCES geographic_area(area_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_event_geographic_area_event ON event_geographic_area (event_id);
CREATE INDEX IF NOT EXISTS idx_event_geographic_area_area ON event_geographic_area (area_id);

-- Function to find events within a radius of a point
CREATE OR REPLACE FUNCTION find_events_within_radius(
    center_lat REAL,
    center_lon REAL,
    radius_meters INTEGER,
    max_results INTEGER DEFAULT 50,
    filter_categories TEXT[] DEFAULT NULL,
    filter_max_price REAL DEFAULT NULL,
    include_expired BOOLEAN DEFAULT false
)
RETURNS TABLE (
    event_id INTEGER,
    title VARCHAR(255),
    description TEXT,
    city TEXT,
    lat REAL,
    lon REAL,
    distance_meters REAL,
    venue_name TEXT,
    address TEXT,
    price DECIMAL(10,2),
    rating REAL,
    categories TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.event_id,
        e.title,
        e.description,
        l.city,
        l.lat,
        l.lon,
        ST_Distance(
            l.geom_mercator,
            ST_Transform(ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326), 3857)
        )::REAL as distance_meters,
        l.name as venue_name,
        l.address,
        e.price,
        COALESCE(e.rating, 0.0) as rating,
        COALESCE(
            ARRAY(
                SELECT ec.name 
                FROM event_category_link ecl 
                JOIN event_category ec ON ecl.category_id = ec.category_id 
                WHERE ecl.event_id = e.event_id
            ), 
            ARRAY[]::VARCHAR[]
        ) as categories
    FROM event e
    INNER JOIN location l ON e.location_id = l.location_id
    WHERE 
        l.geom_mercator IS NOT NULL
        AND e.is_active = true
        AND (include_expired = true OR e.expiry_date IS NULL OR e.expiry_date > NOW())
        AND ST_DWithin(
            l.geom_mercator,
            ST_Transform(ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326), 3857),
            radius_meters
        )
        AND (filter_categories IS NULL OR 
             EXISTS (
                 SELECT 1 FROM event_category_link ecl 
                 JOIN event_category ec ON ecl.category_id = ec.category_id 
                 WHERE ecl.event_id = e.event_id 
                 AND ec.name = ANY(filter_categories)
             ))
        AND (filter_max_price IS NULL OR e.price <= filter_max_price)
    ORDER BY distance_meters ASC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Function to find events within a bounding box
CREATE OR REPLACE FUNCTION find_events_in_bbox(
    min_lat REAL,
    min_lon REAL,
    max_lat REAL,
    max_lon REAL,
    max_results INTEGER DEFAULT 100,
    filter_categories TEXT[] DEFAULT NULL,
    include_expired BOOLEAN DEFAULT false
)
RETURNS TABLE (
    event_id INTEGER,
    title VARCHAR(255),
    city TEXT,
    lat REAL,
    lon REAL,
    venue_name TEXT,
    price DECIMAL(10,2),
    categories TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.event_id,
        e.title,
        l.city,
        l.lat,
        l.lon,
        l.name as venue_name,
        e.price,
        COALESCE(
            ARRAY(
                SELECT ec.name 
                FROM event_category_link ecl 
                JOIN event_category ec ON ecl.category_id = ec.category_id 
                WHERE ecl.event_id = e.event_id
            ), 
            ARRAY[]::VARCHAR[]
        ) as categories
    FROM event e
    INNER JOIN location l ON e.location_id = l.location_id
    WHERE 
        l.geom IS NOT NULL
        AND e.is_active = true
        AND (include_expired = true OR e.expiry_date IS NULL OR e.expiry_date > NOW())
        AND ST_Intersects(
            l.geom,
            ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        )
        AND (filter_categories IS NULL OR 
             EXISTS (
                 SELECT 1 FROM event_category_link ecl 
                 JOIN event_category ec ON ecl.category_id = ec.category_id 
                 WHERE ecl.event_id = e.event_id 
                 AND ec.name = ANY(filter_categories)
             ))
    ORDER BY l.city, e.title
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Function to find events within a named geographic area
CREATE OR REPLACE FUNCTION find_events_in_area(
    area_name TEXT,
    area_type TEXT DEFAULT NULL,
    max_results INTEGER DEFAULT 100,
    include_expired BOOLEAN DEFAULT false
)
RETURNS TABLE (
    event_id INTEGER,
    title VARCHAR(255),
    city TEXT,
    lat REAL,
    lon REAL,
    venue_name TEXT,
    area_name TEXT,
    area_type TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.event_id,
        e.title,
        l.city,
        l.lat,
        l.lon,
        l.name as venue_name,
        ga.name as area_name,
        ga.area_type
    FROM event e
    INNER JOIN location l ON e.location_id = l.location_id
    INNER JOIN event_geographic_area ega ON e.event_id = ega.event_id
    INNER JOIN geographic_area ga ON ega.area_id = ga.area_id
    WHERE 
        e.is_active = true
        AND (include_expired = true OR e.expiry_date IS NULL OR e.expiry_date > NOW())
        AND ga.name ILIKE '%' || area_name || '%'
        AND (area_type IS NULL OR ga.area_type = area_type)
    ORDER BY ga.name, e.title
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Function to auto-assign events to geographic areas based on location
CREATE OR REPLACE FUNCTION assign_events_to_areas()
RETURNS TABLE (
    assigned_count INTEGER,
    area_assignments JSONB
) AS $$
DECLARE
    assignment_count INTEGER := 0;
    assignments JSONB := '[]'::jsonb;
    event_rec RECORD;
    area_rec RECORD;
BEGIN
    -- Clear existing automatic assignments
    DELETE FROM event_geographic_area 
    WHERE area_id IN (
        SELECT area_id FROM geographic_area 
        WHERE metadata->>'auto_assigned' = 'true'
    );
    
    -- For each active event with location
    FOR event_rec IN 
        SELECT e.event_id, l.geom, e.title, l.city
        FROM event e
        INNER JOIN location l ON e.location_id = l.location_id
        WHERE e.is_active = true AND l.geom IS NOT NULL
    LOOP
        -- Find all areas that contain this event's location
        FOR area_rec IN
            SELECT ga.area_id, ga.name, ga.area_type
            FROM geographic_area ga
            WHERE (ga.geom IS NOT NULL AND ST_Contains(ga.geom, event_rec.geom))
               OR (ga.center_point IS NOT NULL AND ga.radius_meters IS NOT NULL 
                   AND ST_DWithin(
                       ST_Transform(ga.center_point, 3857),
                       ST_Transform(event_rec.geom, 3857),
                       ga.radius_meters
                   ))
        LOOP
            -- Insert the assignment
            INSERT INTO event_geographic_area (event_id, area_id)
            VALUES (event_rec.event_id, area_rec.area_id)
            ON CONFLICT DO NOTHING;
            
            assignment_count := assignment_count + 1;
            
            -- Track assignment for reporting
            assignments := assignments || jsonb_build_object(
                'event_id', event_rec.event_id,
                'event_title', event_rec.title,
                'area_id', area_rec.area_id,
                'area_name', area_rec.name,
                'area_type', area_rec.area_type
            );
        END LOOP;
    END LOOP;
    
    RETURN QUERY SELECT assignment_count, assignments;
END;
$$ LANGUAGE plpgsql;

-- Function to get nearby events based on another event's location
CREATE OR REPLACE FUNCTION find_nearby_events(
    source_event_id INTEGER,
    radius_meters INTEGER DEFAULT 5000,
    max_results INTEGER DEFAULT 10,
    exclude_same_venue BOOLEAN DEFAULT true
)
RETURNS TABLE (
    event_id INTEGER,
    title VARCHAR(255),
    distance_meters REAL,
    venue_name TEXT,
    city TEXT,
    similarity_score REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e2.event_id,
        e2.title,
        ST_Distance(
            l1.geom_mercator,
            l2.geom_mercator
        )::REAL as distance_meters,
        l2.name as venue_name,
        l2.city,
        CASE 
            WHEN e1.embedding IS NOT NULL AND e2.embedding IS NOT NULL THEN
                (1 - (e1.embedding <=> e2.embedding))
            ELSE 0.0
        END as similarity_score
    FROM event e1
    INNER JOIN location l1 ON e1.location_id = l1.location_id
    CROSS JOIN event e2
    INNER JOIN location l2 ON e2.location_id = l2.location_id
    WHERE 
        e1.event_id = source_event_id
        AND e2.event_id != source_event_id
        AND e2.is_active = true
        AND (e2.expiry_date IS NULL OR e2.expiry_date > NOW())
        AND l1.geom_mercator IS NOT NULL
        AND l2.geom_mercator IS NOT NULL
        AND ST_DWithin(l1.geom_mercator, l2.geom_mercator, radius_meters)
        AND (exclude_same_venue = false OR l1.location_id != l2.location_id)
    ORDER BY 
        distance_meters ASC,
        similarity_score DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Function to get geographic statistics
CREATE OR REPLACE FUNCTION get_geographic_statistics()
RETURNS TABLE (
    total_locations INTEGER,
    locations_with_coords INTEGER,
    total_areas INTEGER,
    events_with_location INTEGER,
    events_with_area_assignments INTEGER,
    avg_events_per_city REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*)::INTEGER FROM location) as total_locations,
        (SELECT COUNT(*)::INTEGER FROM location WHERE geom IS NOT NULL) as locations_with_coords,
        (SELECT COUNT(*)::INTEGER FROM geographic_area) as total_areas,
        (SELECT COUNT(*)::INTEGER FROM event e 
         INNER JOIN location l ON e.location_id = l.location_id 
         WHERE e.is_active = true) as events_with_location,
        (SELECT COUNT(DISTINCT e.event_id)::INTEGER 
         FROM event e 
         INNER JOIN event_geographic_area ega ON e.event_id = ega.event_id
         WHERE e.is_active = true) as events_with_area_assignments,
        (SELECT ROUND(COUNT(*)::REAL / NULLIF(COUNT(DISTINCT l.city), 0), 2)
         FROM event e 
         INNER JOIN location l ON e.location_id = l.location_id 
         WHERE e.is_active = true AND l.city IS NOT NULL) as avg_events_per_city;
END;
$$ LANGUAGE plpgsql;

-- Insert some common geographic areas (example data)
INSERT INTO geographic_area (name, area_type, city, center_point, radius_meters, metadata) VALUES
('Downtown Core', 'district', 'Toronto', ST_SetSRID(ST_MakePoint(-79.3832, 43.6532), 4326), 2000, '{"auto_assigned": true}'),
('Entertainment District', 'district', 'Toronto', ST_SetSRID(ST_MakePoint(-79.3900, 43.6426), 4326), 1500, '{"auto_assigned": true}'),
('Waterfront', 'district', 'Toronto', ST_SetSRID(ST_MakePoint(-79.3776, 43.6426), 4326), 2500, '{"auto_assigned": true}'),
('Old Montreal', 'district', 'Montreal', ST_SetSRID(ST_MakePoint(-73.5549, 45.5088), 4326), 1200, '{"auto_assigned": true}'),
('Gastown', 'neighborhood', 'Vancouver', ST_SetSRID(ST_MakePoint(-123.1043, 49.2839), 4326), 800, '{"auto_assigned": true}'),
('Granville Island', 'district', 'Vancouver', ST_SetSRID(ST_MakePoint(-123.1349, 49.2713), 4326), 500, '{"auto_assigned": true}')
ON CONFLICT DO NOTHING;

-- Add comments
COMMENT ON COLUMN location.geom IS 'PostGIS geometry point in WGS84 (SRID 4326)';
COMMENT ON COLUMN location.geom_mercator IS 'PostGIS geometry point in Web Mercator (SRID 3857) for distance calculations';
COMMENT ON TABLE geographic_area IS 'Named geographic regions for organizing events';
COMMENT ON TABLE event_geographic_area IS 'Many-to-many relationship between events and geographic areas';

-- Grant necessary permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON geographic_area TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON event_geographic_area TO your_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_app_user;