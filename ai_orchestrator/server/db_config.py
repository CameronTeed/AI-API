import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
import os
import logging
from typing import Optional
from contextlib import contextmanager
import threading

# Load environment variables from .env
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Try to import async psycopg for enhanced features
try:
    import psycopg
    from psycopg_pool import ConnectionPool
    ASYNC_SUPPORT = True
except ImportError:
    ASYNC_SUPPORT = False
    logger.warning("psycopg (async) not available - enhanced features will use sync fallback")

# Set up logging
logger = logging.getLogger(__name__)

# Fetch variables
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
HOST = os.getenv("DB_HOST")
PORT = os.getenv("DB_PORT")
DBNAME = os.getenv("DB_NAME")

class DatabaseConfig:
    """Database configuration and connection management with connection pooling"""
    
    def __init__(self):
        self.host = HOST
        self.port = int(PORT) if PORT else 5432
        self.database = DBNAME
        self.user = USER
        self.password = PASSWORD
        
        # Connection pool settings
        self.min_connections = int(os.getenv("DB_MIN_CONNECTIONS", "2"))
        self.max_connections = int(os.getenv("DB_MAX_CONNECTIONS", "10"))
        
        # Connection pool
        self._pool = None
        self._pool_lock = threading.Lock()
        
        # Async connection pool (for enhanced features)
        self._async_pool = None
        
        # Connection parameters for session pooling optimization
        self.connection_params = {
            'user': self.user,
            'password': self.password,
            'host': self.host,
            'port': self.port,
            'dbname': self.database,
            # Optimize for session pooling
            'connect_timeout': 30,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 3,
            'application_name': 'ai_orchestrator'
        }
        
        logger.info(f"Database config: {self.host}:{self.port}/{self.database}")
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool"""
        try:
            with self._pool_lock:
                if self._pool is None:
                    self._pool = psycopg2.pool.ThreadedConnectionPool(
                        minconn=self.min_connections,
                        maxconn=self.max_connections,
                        **self.connection_params
                    )
                    logger.info(f"Initialized connection pool with {self.min_connections}-{self.max_connections} connections")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    def _get_pool_connection(self):
        """Get a connection from the pool"""
        if self._pool is None:
            self._initialize_pool()
        
        try:
            return self._pool.getconn()
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise
    
    def _return_pool_connection(self, conn, close=False):
        """Return a connection to the pool"""
        if self._pool and conn:
            try:
                self._pool.putconn(conn, close=close)
            except Exception as e:
                logger.error(f"Failed to return connection to pool: {e}")
    
    @property
    def connection_string(self) -> str:
        """Get the connection string for PostgreSQL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool with proper cleanup"""
        conn = None
        try:
            conn = self._get_pool_connection()
            if conn.closed:
                # Connection is closed, mark it for replacement
                self._return_pool_connection(conn, close=True)
                conn = self._get_pool_connection()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            # Return connection as closed so pool creates a new one
            if conn:
                self._return_pool_connection(conn, close=True)
            raise
        else:
            # Connection was used successfully, return to pool
            if conn:
                self._return_pool_connection(conn, close=False)
    
    def close_pool(self):
        """Close all connections in the pool"""
        with self._pool_lock:
            if self._pool:
                self._pool.closeall()
                self._pool = None
                logger.info("Connection pool closed")
    
    async def get_async_pool(self):
        """Get or create async connection pool for enhanced features"""
        if not ASYNC_SUPPORT:
            raise ImportError("Async database support not available. Install psycopg[binary] and psycopg-pool")
        
        if self._async_pool is None:
            try:
                # Create async connection pool
                self._async_pool = ConnectionPool(
                    self.connection_string,
                    min_size=self.min_connections,
                    max_size=self.max_connections,
                    kwargs={
                        'autocommit': True
                    }
                )
                await self._async_pool.open()
                logger.info(f"Initialized async connection pool with {self.min_connections}-{self.max_connections} connections")
            except Exception as e:
                logger.error(f"Failed to initialize async connection pool: {e}")
                raise
        
        return self._async_pool
    
    async def close_async_pool(self):
        """Close the async connection pool"""
        if self._async_pool:
            await self._async_pool.close()
            self._async_pool = None
            logger.info("Async connection pool closed")

# Global instance
_db_config: Optional[DatabaseConfig] = None

def get_db_config() -> DatabaseConfig:
    """Get the global database configuration instance"""
    global _db_config
    if _db_config is None:
        _db_config = DatabaseConfig()
    return _db_config

async def get_db_pool():
    """Get the async database pool for enhanced features"""
    config = get_db_config()
    return await config.get_async_pool()

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

# Supabase example connection (run when script is executed directly)
if __name__ == "__main__":
    # Connect to the database
    try:
        connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
        print("Connection successful!")
        
        # Create a cursor to execute SQL queries
        cursor = connection.cursor()
        
        # Example query
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        print("Current Time:", result)

        # Close the cursor and connection
        cursor.close()
        connection.close()
        print("Connection closed.")

    except Exception as e:
        print(f"Failed to connect: {e}")