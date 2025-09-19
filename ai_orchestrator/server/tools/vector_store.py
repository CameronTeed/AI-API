"""
Vector store for date ideas using sentence transformers for embeddings
and efficient similarity search.

This module now uses PostgreSQL with pgvector for production,
with file-based fallback for development/testing.
"""

# Import the new PostgreSQL-backed implementation
from .postgresql_vector_store import PostgreSQLVectorStore, get_vector_store

# For backwards compatibility, also expose the old class name
DateIdeaVectorStore = PostgreSQLVectorStore

# Export the main interface
__all__ = ['PostgreSQLVectorStore', 'DateIdeaVectorStore', 'get_vector_store']
