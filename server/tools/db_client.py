"""
Legacy database client - now deprecated in favor of vector store.
This module is kept for backwards compatibility but no longer used.
"""
import logging

logger = logging.getLogger(__name__)

class DatabaseClient:
    """Deprecated database client - use vector store instead"""
    
    def __init__(self):
        logger.warning("DatabaseClient is deprecated. Use vector_store.py instead.")
    
    async def search_dates_db(self, **kwargs):
        """Deprecated method - use vector store instead"""
        logger.warning("search_dates_db is deprecated. Use vector store search instead.")
        return {"items": [], "source": "db", "error": "Database client deprecated - use vector store"}
    
    def close(self):
        """No-op close method"""
        pass

# Global instance for backwards compatibility
_db_client = None

def get_db_client() -> DatabaseClient:
    """Get global database client instance - deprecated"""
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client
