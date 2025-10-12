"""
Chat Context Storage System
Handles storing and retrieving chat conversations for future use
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import psycopg
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

class ChatContextStorage:
    """Manages chat context storage and retrieval"""
    
    def __init__(self):
        logger.debug("🔧 Initializing ChatContextStorage")
        
        # Database connection configuration
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'dbname': os.getenv('DB_NAME', 'ai_orchestrator')
        }
        
        # Connection string
        self.connection_string = f"postgresql://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['dbname']}"
        
        # Connection pool
        self.pool = None
        self._initialize_pool()
        
        logger.info("✅ ChatContextStorage initialized")

    def _initialize_pool(self):
        """Initialize async connection pool"""
        try:
            self.pool = AsyncConnectionPool(
                self.connection_string,
                min_size=1,
                max_size=5,
                timeout=30
            )
            logger.debug("✅ Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            self.pool = None

    async def ensure_tables_exist(self):
        """Ensure chat-related tables exist in the database"""
        if not self.pool:
            logger.error("No database connection pool available")
            return False
        
        try:
            async with self.pool.connection() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        session_id VARCHAR(255) PRIMARY KEY,
                        user_id VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        session_metadata JSONB DEFAULT '{}'::jsonb,
                        is_active BOOLEAN DEFAULT TRUE
                    );
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        message_id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                        role VARCHAR(50) NOT NULL, -- 'user', 'assistant', 'system'
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        message_metadata JSONB DEFAULT '{}'::jsonb,
                        token_count INTEGER,
                        embedding vector(384) -- For semantic search of chat history
                    );
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS chat_tool_calls (
                        call_id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                        message_id INTEGER REFERENCES chat_messages(message_id) ON DELETE CASCADE,
                        tool_name VARCHAR(255) NOT NULL,
                        tool_arguments JSONB,
                        tool_result JSONB,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        execution_time_ms INTEGER
                    );
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS chat_context_summaries (
                        summary_id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                        summary_text TEXT,
                        message_range_start INTEGER,
                        message_range_end INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        summary_embedding vector(384)
                    );
                """)
                
                # Create indexes for performance
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_messages_session_timestamp 
                    ON chat_messages(session_id, timestamp);
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_active 
                    ON chat_sessions(user_id, is_active);
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_tool_calls_session 
                    ON chat_tool_calls(session_id, timestamp);
                """)
                
                await conn.commit()
                logger.info("✅ Chat context tables created/verified")
                return True
                
        except Exception as e:
            logger.error(f"Error creating chat context tables: {e}")
            return False

    async def create_session(self, session_id: str, user_id: Optional[str] = None, metadata: Optional[Dict] = None) -> bool:
        """Create a new chat session"""
        if not self.pool:
            return False
        
        try:
            async with self.pool.connection() as conn:
                await conn.execute("""
                    INSERT INTO chat_sessions (session_id, user_id, session_metadata)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (session_id) DO UPDATE SET
                        updated_at = CURRENT_TIMESTAMP,
                        is_active = TRUE
                """, (session_id, user_id, json.dumps(metadata or {})))
                
                await conn.commit()
                logger.info(f"✅ Chat session created: {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error creating chat session {session_id}: {e}")
            return False

    async def store_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        metadata: Optional[Dict] = None,
        embedding: Optional[List[float]] = None
    ) -> Optional[int]:
        """Store a chat message"""
        if not self.pool:
            return None
        
        try:
            async with self.pool.connection() as conn:
                result = await conn.execute("""
                    INSERT INTO chat_messages (session_id, role, content, message_metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING message_id
                """, (
                    session_id, 
                    role, 
                    content, 
                    json.dumps(metadata or {}),
                    embedding
                ))
                
                message_id = (await result.fetchone())[0]
                await conn.commit()
                
                logger.debug(f"📝 Message stored: {message_id} in session {session_id}")
                return message_id
                
        except Exception as e:
            logger.error(f"Error storing message in session {session_id}: {e}")
            return None

    async def store_tool_call(
        self, 
        session_id: str, 
        message_id: int,
        tool_name: str,
        tool_arguments: Dict,
        tool_result: Dict,
        execution_time_ms: Optional[int] = None
    ) -> bool:
        """Store a tool call record"""
        if not self.pool:
            return False
        
        # Skip storing if message_id is 0 (placeholder value)
        if message_id == 0:
            logger.debug(f"🔧 Skipping tool call storage for {tool_name} - message_id not tracked yet")
            return True
        
        try:
            async with self.pool.connection() as conn:
                await conn.execute("""
                    INSERT INTO chat_tool_calls 
                    (session_id, message_id, tool_name, tool_arguments, tool_result, execution_time_ms)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    session_id,
                    message_id, 
                    tool_name,
                    json.dumps(tool_arguments),
                    json.dumps(tool_result),
                    execution_time_ms
                ))
                
                await conn.commit()
                logger.debug(f"🔧 Tool call stored: {tool_name} for session {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error storing tool call: {e}")
            return False

    async def get_session_messages(
        self, 
        session_id: str, 
        limit: Optional[int] = None,
        include_system: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieve messages from a chat session"""
        if not self.pool:
            return []
        
        try:
            async with self.pool.connection() as conn:
                query = """
                    SELECT message_id, role, content, timestamp, message_metadata, token_count
                    FROM chat_messages 
                    WHERE session_id = %s
                """
                params = [session_id]
                
                if not include_system:
                    query += " AND role != 'system'"
                
                query += " ORDER BY timestamp ASC"
                
                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                
                result = await conn.execute(query, params)
                rows = await result.fetchall()
                
                messages = []
                for row in rows:
                    messages.append({
                        'message_id': row[0],
                        'role': row[1],
                        'content': row[2],
                        'timestamp': row[3].isoformat(),
                        'metadata': row[4] if row[4] else {},
                        'token_count': row[5]
                    })
                
                logger.debug(f"📚 Retrieved {len(messages)} messages for session {session_id}")
                return messages
                
        except Exception as e:
            logger.error(f"Error retrieving messages for session {session_id}: {e}")
            return []

    async def get_session_context(self, session_id: str, context_length: int = 10) -> Dict[str, Any]:
        """Get recent context for a chat session"""
        if not self.pool:
            return {"messages": [], "summaries": [], "tool_calls": []}
        
        try:
            # Get recent messages
            messages = await self.get_session_messages(session_id, limit=context_length)
            
            # Get recent tool calls
            async with self.pool.connection() as conn:
                tool_result = await conn.execute("""
                    SELECT tool_name, tool_arguments, tool_result, timestamp, execution_time_ms
                    FROM chat_tool_calls 
                    WHERE session_id = %s 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """, (session_id, context_length))
                
                tool_calls = []
                for row in await tool_result.fetchall():
                    tool_calls.append({
                        'tool_name': row[0],
                        'arguments': row[1],
                        'result': row[2],
                        'timestamp': row[3].isoformat(),
                        'execution_time_ms': row[4]
                    })
                
                # Get session summaries
                summary_result = await conn.execute("""
                    SELECT summary_text, message_range_start, message_range_end, created_at
                    FROM chat_context_summaries 
                    WHERE session_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT 3
                """, (session_id,))
                
                summaries = []
                for row in await summary_result.fetchall():
                    summaries.append({
                        'summary': row[0],
                        'message_range': f"{row[1]}-{row[2]}",
                        'created_at': row[3].isoformat()
                    })
            
            return {
                "messages": messages,
                "tool_calls": tool_calls,
                "summaries": summaries
            }
            
        except Exception as e:
            logger.error(f"Error getting session context for {session_id}: {e}")
            return {"messages": [], "summaries": [], "tool_calls": []}

    async def search_chat_history(
        self, 
        user_id: Optional[str] = None,
        query: Optional[str] = None,
        session_ids: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search across chat history"""
        if not self.pool:
            return []
        
        try:
            async with self.pool.connection() as conn:
                base_query = """
                    SELECT DISTINCT s.session_id, s.user_id, s.created_at, s.updated_at, 
                           s.session_metadata, m.content, m.timestamp, m.role
                    FROM chat_sessions s
                    LEFT JOIN chat_messages m ON s.session_id = m.session_id
                    WHERE s.is_active = TRUE
                """
                params = []
                
                if user_id:
                    base_query += " AND s.user_id = %s"
                    params.append(user_id)
                
                if session_ids:
                    placeholders = ','.join(['%s'] * len(session_ids))
                    base_query += f" AND s.session_id IN ({placeholders})"
                    params.extend(session_ids)
                
                if query:
                    base_query += " AND m.content ILIKE %s"
                    params.append(f"%{query}%")
                
                base_query += " ORDER BY m.timestamp DESC LIMIT %s"
                params.append(limit)
                
                result = await conn.execute(base_query, params)
                rows = await result.fetchall()
                
                search_results = []
                for row in rows:
                    search_results.append({
                        'session_id': row[0],
                        'user_id': row[1],
                        'session_created': row[2].isoformat(),
                        'session_updated': row[3].isoformat(),
                        'session_metadata': row[4],
                        'message_content': row[5],
                        'message_timestamp': row[6].isoformat() if row[6] else None,
                        'message_role': row[7]
                    })
                
                logger.debug(f"🔍 Found {len(search_results)} chat history results")
                return search_results
                
        except Exception as e:
            logger.error(f"Error searching chat history: {e}")
            return []

    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up old inactive sessions"""
        if not self.pool:
            return 0
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            async with self.pool.connection() as conn:
                result = await conn.execute("""
                    DELETE FROM chat_sessions 
                    WHERE updated_at < %s AND is_active = FALSE
                    RETURNING session_id
                """, (cutoff_date,))
                
                deleted_sessions = await result.fetchall()
                await conn.commit()
                
                count = len(deleted_sessions)
                logger.info(f"🧹 Cleaned up {count} old chat sessions")
                return count
                
        except Exception as e:
            logger.error(f"Error cleaning up old sessions: {e}")
            return 0

    async def deactivate_session(self, session_id: str) -> bool:
        """Mark a session as inactive"""
        if not self.pool:
            return False
        
        try:
            async with self.pool.connection() as conn:
                await conn.execute("""
                    UPDATE chat_sessions 
                    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = %s
                """, (session_id,))
                
                await conn.commit()
                logger.info(f"🔒 Session deactivated: {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deactivating session {session_id}: {e}")
            return False

    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("🔌 Chat context storage connection pool closed")

# Global instance
_chat_storage = None

def get_chat_storage() -> ChatContextStorage:
    """Get global chat storage instance"""
    global _chat_storage
    if _chat_storage is None:
        _chat_storage = ChatContextStorage()
    return _chat_storage