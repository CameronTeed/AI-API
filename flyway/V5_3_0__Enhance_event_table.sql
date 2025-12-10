-- Flyway Migration: Enhance event table for AI capabilities
-- Migration version: V1.3.0
-- Description: Add AI-related columns to event table for vector search and enhanced metadata
-- Author: AI Orchestrator Integration  
-- Date: 2025-09-13

-- Add AI and vector search related columns to event table
ALTER TABLE event 
ADD COLUMN IF NOT EXISTS duration_min INTEGER,
ADD COLUMN IF NOT EXISTS indoor BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS kid_friendly BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS website TEXT,
ADD COLUMN IF NOT EXISTS phone TEXT,
ADD COLUMN IF NOT EXISTS rating REAL DEFAULT 0.0 CHECK (rating >= 0.0 AND rating <= 5.0),
ADD COLUMN IF NOT EXISTS review_count INTEGER DEFAULT 0 CHECK (review_count >= 0),
ADD COLUMN IF NOT EXISTS embedding vector(384),
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Add indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_event_duration ON event (duration_min) WHERE duration_min IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_event_indoor ON event (indoor);
CREATE INDEX IF NOT EXISTS idx_event_kid_friendly ON event (kid_friendly);
CREATE INDEX IF NOT EXISTS idx_event_rating ON event (rating DESC) WHERE rating > 0;
CREATE INDEX IF NOT EXISTS idx_event_ai_recommended ON event (is_ai_recommended);
CREATE INDEX IF NOT EXISTS idx_event_metadata ON event USING GIN (metadata) WHERE metadata != '{}'::jsonb;

-- Vector similarity search index using HNSW (Hierarchical Navigable Small World)
-- This enables fast approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS idx_event_embedding ON event 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64)
WHERE embedding IS NOT NULL;

-- Add column comments for documentation
COMMENT ON COLUMN event.duration_min IS 'AI Orchestrator: Event duration in minutes for filtering';
COMMENT ON COLUMN event.indoor IS 'AI Orchestrator: True if indoor activity, false if outdoor';
COMMENT ON COLUMN event.kid_friendly IS 'AI Orchestrator: True if suitable for children';
COMMENT ON COLUMN event.website IS 'AI Orchestrator: Event or venue website URL';
COMMENT ON COLUMN event.phone IS 'AI Orchestrator: Contact phone number';
COMMENT ON COLUMN event.rating IS 'AI Orchestrator: Average rating from 0.0 to 5.0';
COMMENT ON COLUMN event.review_count IS 'AI Orchestrator: Number of reviews';
COMMENT ON COLUMN event.embedding IS 'AI Orchestrator: 384-dimensional vector for semantic similarity search';
COMMENT ON COLUMN event.metadata IS 'AI Orchestrator: Additional flexible metadata as JSON';