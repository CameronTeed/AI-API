#!/usr/bin/env python3
"""
Script to populate the vector store with sample date ideas data.
Run this to initialize the knowledge base with PostgreSQL backend.
"""
import json
import os
import sys
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not available. Make sure to set environment variables manually.")

# Add the parent directory to the path so we can import from server
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from server.tools.vector_store import get_vector_store
from server.db_config import test_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_sample_data():
    """Load sample date ideas from JSON file"""
    sample_file = os.path.join(os.path.dirname(__file__), 'data', 'sample_date_ideas.json')
    
    try:
        with open(sample_file, 'r') as f:
            date_ideas = json.load(f)
        logger.info(f"Loaded {len(date_ideas)} sample date ideas")
        return date_ideas
    except Exception as e:
        logger.error(f"Failed to load sample data: {e}")
        return []

def validate_date_ideas(date_ideas):
    """Validate and ensure date ideas have required fields"""
    validated_ideas = []
    
    for i, idea in enumerate(date_ideas):
        # Ensure ID exists
        if not idea.get("id"):
            idea["id"] = f"sample_idea_{i+1}"
        
        # Ensure required fields have defaults
        idea.setdefault("title", "Untitled Date Idea")
        idea.setdefault("description", "")
        idea.setdefault("categories", [])
        idea.setdefault("city", "")
        idea.setdefault("lat", 0.0)
        idea.setdefault("lon", 0.0)
        idea.setdefault("price_tier", 1)
        idea.setdefault("duration_min", 60)
        idea.setdefault("indoor", False)
        idea.setdefault("kid_friendly", False)
        idea.setdefault("website", "")
        idea.setdefault("phone", "")
        idea.setdefault("rating", 0.0)
        idea.setdefault("review_count", 0)
        
        validated_ideas.append(idea)
    
    return validated_ideas

def populate_vector_store():
    """Populate the vector store with sample data"""
    logger.info("🚀 Initializing vector store with PostgreSQL backend...")
    
    # Test database connection first
    logger.info("🔍 Testing database connection...")
    db_available = test_connection()
    if not db_available:
        logger.warning("⚠️  PostgreSQL connection failed!")
        logger.info("Will use file-based fallback storage instead.")
        logger.info("For PostgreSQL setup, please ensure:")
        logger.info("1. PostgreSQL is running")
        logger.info("2. Database exists and pgvector extension is installed")
        logger.info("3. Run: python init_database.py")
        logger.info("4. Set environment variables: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD")
    else:
        logger.info("✅ Database connection successful")
    
    # Get the vector store instance
    vector_store = get_vector_store()
    
    # Check if sentence-transformers is available
    if not hasattr(vector_store, 'model') or vector_store.model is None:
        logger.error("❌ Vector store model not available. Please install sentence-transformers:")
        logger.error("pip install sentence-transformers")
        return False
    
    logger.info("✅ Sentence transformer model loaded")
    
    # Load sample data
    logger.info("📂 Loading sample data...")
    date_ideas = load_sample_data()
    if not date_ideas:
        logger.error("❌ No sample data to load")
        return False
    
    # Validate data
    logger.info("🔍 Validating date ideas...")
    validated_ideas = validate_date_ideas(date_ideas)
    logger.info(f"✅ Validated {len(validated_ideas)} date ideas")
    
    # Add to vector store
    logger.info("💾 Adding date ideas to PostgreSQL vector store...")
    if vector_store.add_date_ideas(validated_ideas):
        logger.info("✅ Successfully added date ideas to vector store")
    else:
        logger.error("❌ Failed to add date ideas to vector store")
        return False
    
    # Show stats
    logger.info("📊 Getting vector store statistics...")
    stats = vector_store.get_stats()
    logger.info(f"Vector store stats: {stats}")
    
    # Test search
    logger.info("🔍 Testing search functionality...")
    test_queries = [
        "romantic dinner for two",
        "outdoor adventure",
        "budget-friendly fun",
        "family activities"
    ]
    
    for query in test_queries:
        logger.info(f"Searching for: '{query}'")
        results = vector_store.search(query, top_k=3)
        logger.info(f"  Found {len(results)} results")
        
        for i, result in enumerate(results, 1):
            similarity = result.get('similarity_score', 0)
            source = result.get('source', 'unknown')
            logger.info(f"    {i}. {result['title']} (similarity: {similarity:.3f}, source: {source})")
    
    return True

def main():
    """Main function"""
    logger.info("🎯 AI Orchestrator Vector Store Population")
    logger.info("=" * 50)
    
    success = populate_vector_store()
    
    if success:
        logger.info("🎉 Vector store populated successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Test the application: python -m server.main")
        logger.info("2. Run tests: python -m pytest tests/")
        logger.info("3. Try the REST API: python rest_api_wrapper.py")
    else:
        logger.error("💥 Failed to populate vector store")
        sys.exit(1)

if __name__ == "__main__":
    main()
