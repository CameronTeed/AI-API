"""
Database configuration for PostgreSQL with pgvector support
"""
import os
import logging
from typing import Optional
import psycopg
from contextlib import asynccontextmanager, contextmanager

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration and connection management"""
    
    def __init__(self):
        # Default values for development
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", "5432"))
        self.database = os.getenv("DB_NAME", "ai_orchestrator")
        self.user = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD", "postgres")
        
        # Connection pool settings
        self.min_connections = int(os.getenv("DB_MIN_CONNECTIONS", "1"))
        self.max_connections = int(os.getenv("DB_MAX_CONNECTIONS", "10"))
        
        logger.info(f"Database config: {self.host}:{self.port}/{self.database}")
    
    @property
    def connection_string(self) -> str:
        """Get the connection string for PostgreSQL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @contextmanager
    def get_connection(self):
        """Get a synchronous database connection"""
        conn = None
        try:
            conn = psycopg.connect(self.connection_string)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    @asynccontextmanager
    async def get_async_connection(self):
        """Get an asynchronous database connection"""
        conn = None
        try:
            conn = await psycopg.AsyncConnection.connect(self.connection_string)
            yield conn
        except Exception as e:
            if conn:
                await conn.rollback()
            logger.error(f"Async database connection error: {e}")
            raise
        finally:
            if conn:
                await conn.close()

# Global instance
_db_config: Optional[DatabaseConfig] = None

def get_db_config() -> DatabaseConfig:
    """Get the global database configuration instance"""
    global _db_config
    if _db_config is None:
        _db_config = DatabaseConfig()
    return _db_config

def test_connection() -> bool:
    """Test database connectivity"""
    try:
        config = get_db_config()
        with config.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                logger.info("Database connection test successful")
                return result[0] == 1
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False