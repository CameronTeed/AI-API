-- Flyway Migration: Enhance existing schema for AI vector search
-- Migration version: V1.2.0  
-- Description: Add vector and AI-related columns to existing tables
-- Author: AI Orchestrator Integration
-- Date: 2025-09-13

-- Enhance location table with coordinates for geographic search
ALTER TABLE location 
ADD COLUMN IF NOT EXISTS lat REAL,
ADD COLUMN IF NOT EXISTS lon REAL;

-- Add indexes for location coordinates
CREATE INDEX IF NOT EXISTS idx_location_coordinates ON location (lat, lon) WHERE lat IS NOT NULL AND lon IS NOT NULL;

-- Add comment
COMMENT ON COLUMN location.lat IS 'AI Orchestrator: Latitude for geographic search';
COMMENT ON COLUMN location.lon IS 'AI Orchestrator: Longitude for geographic search';