"""
Vector Search Tool - Consolidated implementation
Uses PostgreSQL with pgvector for semantic search of date ideas.

This is the main vector search implementation. All other vector search files
(vector_store.py, postgresql_vector_store.py, consolidated_vector_search.py)
are deprecated and should use this module instead.
"""

# Import the actual implementation from postgresql_vector_store
from .postgresql_vector_store import PostgreSQLVectorStore, get_vector_store

# For backwards compatibility, expose both names
VectorStore = PostgreSQLVectorStore
DateIdeaVectorStore = PostgreSQLVectorStore

# Export the main interface
__all__ = ['PostgreSQLVectorStore', 'VectorStore', 'DateIdeaVectorStore', 'get_vector_store']

