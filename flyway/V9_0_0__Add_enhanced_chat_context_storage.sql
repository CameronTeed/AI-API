-- Enhanced Chat Context Storage Migration
-- Adds tables for storing chat conversations and context
-- Compatible with existing AI Orchestrator schema

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===== CHAT CONTEXT STORAGE TABLES =====

-- Chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    session_type VARCHAR(50) DEFAULT 'chat', -- 'chat', 'api', 'web_ui'
    client_info TEXT,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat messages table with vector embeddings for semantic search
CREATE TABLE IF NOT EXISTS chat_messages (
    message_id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_metadata JSONB DEFAULT '{}'::jsonb,
    token_count INTEGER,
    embedding vector(384), -- For semantic search of chat history
    parent_message_id INTEGER REFERENCES chat_messages(message_id),
    message_type VARCHAR(50) DEFAULT 'text' -- 'text', 'structured', 'error'
);

-- Tool calls and results tracking
CREATE TABLE IF NOT EXISTS chat_tool_calls (
    call_id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    message_id INTEGER REFERENCES chat_messages(message_id) ON DELETE CASCADE,
    tool_name VARCHAR(255) NOT NULL,
    tool_arguments JSONB,
    tool_result JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Chat context summaries for long conversations
CREATE TABLE IF NOT EXISTS chat_context_summaries (
    summary_id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    summary_text TEXT,
    message_range_start INTEGER,
    message_range_end INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    summary_embedding vector(384),
    summary_type VARCHAR(50) DEFAULT 'auto', -- 'auto', 'manual', 'periodic'
    tokens_saved INTEGER -- How many tokens this summary saves
);

-- User preferences and settings
CREATE TABLE IF NOT EXISTS user_chat_preferences (
    user_id VARCHAR(255) PRIMARY KEY,
    preferences JSONB DEFAULT '{}'::jsonb,
    default_city VARCHAR(255),
    default_constraints JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timezone VARCHAR(50) DEFAULT 'UTC'
);

-- Chat feedback and ratings
CREATE TABLE IF NOT EXISTS chat_feedback (
    feedback_id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    message_id INTEGER REFERENCES chat_messages(message_id) ON DELETE CASCADE,
    user_id VARCHAR(255),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    feedback_type VARCHAR(50), -- 'rating', 'bug_report', 'suggestion'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE
);

-- ===== PERFORMANCE INDEXES =====

-- Indexes for chat messages
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_timestamp 
ON chat_messages(session_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_chat_messages_role_timestamp 
ON chat_messages(role, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_chat_messages_embedding 
ON chat_messages USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Indexes for chat sessions
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_active 
ON chat_sessions(user_id, is_active, last_activity DESC);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_created 
ON chat_sessions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_active 
ON chat_sessions(is_active, last_activity DESC);

-- Indexes for tool calls
CREATE INDEX IF NOT EXISTS idx_chat_tool_calls_session 
ON chat_tool_calls(session_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_chat_tool_calls_tool_name 
ON chat_tool_calls(tool_name, timestamp DESC);

-- Indexes for summaries
CREATE INDEX IF NOT EXISTS idx_chat_summaries_session 
ON chat_context_summaries(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_summaries_embedding 
ON chat_context_summaries USING ivfflat (summary_embedding vector_cosine_ops)
WITH (lists = 50);

-- Indexes for feedback
CREATE INDEX IF NOT EXISTS idx_chat_feedback_session 
ON chat_feedback(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_feedback_user 
ON chat_feedback(user_id, created_at DESC);

-- ===== TRIGGERS FOR AUTOMATIC UPDATES =====

-- Update last_activity on chat_sessions when messages are added
CREATE OR REPLACE FUNCTION update_session_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chat_sessions 
    SET last_activity = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE session_id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_session_activity ON chat_messages;
CREATE TRIGGER trigger_update_session_activity
    AFTER INSERT ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_session_activity();

-- Update user preferences timestamp
CREATE OR REPLACE FUNCTION update_user_preferences_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_user_preferences ON user_chat_preferences;
CREATE TRIGGER trigger_update_user_preferences
    BEFORE UPDATE ON user_chat_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_user_preferences_timestamp();

-- ===== CHAT CONTEXT VIEWS =====

-- View for recent chat activity
CREATE OR REPLACE VIEW recent_chat_activity AS
SELECT 
    s.session_id,
    s.user_id,
    s.created_at as session_start,
    s.last_activity,
    COUNT(m.message_id) as message_count,
    MAX(m.timestamp) as last_message,
    COUNT(DISTINCT tc.tool_name) as tools_used
FROM chat_sessions s
LEFT JOIN chat_messages m ON s.session_id = m.session_id
LEFT JOIN chat_tool_calls tc ON s.session_id = tc.session_id
WHERE s.is_active = TRUE
GROUP BY s.session_id, s.user_id, s.created_at, s.last_activity
ORDER BY s.last_activity DESC;

-- View for user chat statistics
CREATE OR REPLACE VIEW user_chat_stats AS
SELECT 
    s.user_id,
    COUNT(DISTINCT s.session_id) as total_sessions,
    COUNT(m.message_id) as total_messages,
    COUNT(tc.call_id) as total_tool_calls,
    AVG(cf.rating) as average_rating,
    MIN(s.created_at) as first_session,
    MAX(s.last_activity) as last_activity
FROM chat_sessions s
LEFT JOIN chat_messages m ON s.session_id = m.session_id
LEFT JOIN chat_tool_calls tc ON s.session_id = tc.session_id
LEFT JOIN chat_feedback cf ON s.session_id = cf.session_id
WHERE s.user_id IS NOT NULL
GROUP BY s.user_id;

-- ===== CLEANUP FUNCTIONS =====

-- Function to clean up old inactive sessions
CREATE OR REPLACE FUNCTION cleanup_old_chat_sessions(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM chat_sessions 
    WHERE last_activity < (CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old)
    AND is_active = FALSE;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to archive old messages (move to archive table or delete)
CREATE OR REPLACE FUNCTION archive_old_chat_messages(days_old INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    DELETE FROM chat_messages 
    WHERE timestamp < (CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old)
    AND session_id IN (
        SELECT session_id FROM chat_sessions WHERE is_active = FALSE
    );
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- ===== SAMPLE DATA FOR TESTING =====

-- Insert a sample user preference
INSERT INTO user_chat_preferences (user_id, preferences, default_city, default_constraints)
VALUES (
    'sample_user',
    '{"language": "en", "date_format": "YYYY-MM-DD", "time_format": "24h"}',
    'Ottawa',
    '{"budgetTier": 2, "indoor": false}'
) ON CONFLICT (user_id) DO NOTHING;

-- ===== COMPLETION MESSAGE =====
DO $$
BEGIN
    RAISE NOTICE 'Enhanced Chat Context Storage Migration Completed Successfully!';
    RAISE NOTICE 'Tables created: chat_sessions, chat_messages, chat_tool_calls, chat_context_summaries, user_chat_preferences, chat_feedback';
    RAISE NOTICE 'Views created: recent_chat_activity, user_chat_stats';
    RAISE NOTICE 'Functions created: cleanup_old_chat_sessions, archive_old_chat_messages';
    RAISE NOTICE 'Ready for enhanced AI chat with context storage!';
END;
$$;