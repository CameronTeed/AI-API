-- Flyway Migration: Add pgvector extension and vector capabilities
-- Migration version: V1.1.0
-- Description: Add pgvector extension for AI vector search capabilities
-- Author: AI Orchestrator Integration
-- Date: 2025-09-13

-- Enable pgvector extension for vector similarity search
-- Note: This requires superuser privileges or the extension to be whitelisted
CREATE EXTENSION IF NOT EXISTS vector;

-- Add comment for tracking
COMMENT ON EXTENSION vector IS 'AI Orchestrator: Vector similarity search for semantic date idea matching';