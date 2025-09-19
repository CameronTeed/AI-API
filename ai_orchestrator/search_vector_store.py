#!/usr/bin/env python3
"""
Script to search the existing vector store in PostgreSQL database.
This searches the vectors that are already stored, rather than adding new data.
"""
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

def search_existing_vectors():
    """Search the existing vectors in the PostgreSQL database"""
    logger.info("🔍 Searching existing vectors in PostgreSQL database...")
    
    # Test database connection first
    logger.info("🔗 Testing database connection...")
    db_available = test_connection()
    if not db_available:
        logger.error("❌ PostgreSQL connection failed!")
        logger.error("Cannot search vectors without database connection.")
        return False
    
    logger.info("✅ Database connection successful")
    
    # Get the vector store instance
    vector_store = get_vector_store()
    
    # Check if sentence-transformers is available
    if not hasattr(vector_store, 'model') or vector_store.model is None:
        logger.error("❌ Vector store model not available. Please install sentence-transformers:")
        logger.error("pip install sentence-transformers")
        return False
    
    logger.info("✅ Sentence transformer model loaded")
    
    # Show stats
    logger.info("📊 Getting vector store statistics...")
    stats = vector_store.get_stats()
    logger.info(f"Vector store stats: {stats}")
    
    # Test search queries
    logger.info("🔍 Testing search functionality on existing database vectors...")
    test_queries = [
        "romantic dinner for two",
        "outdoor adventure activities", 
        "budget-friendly fun date",
        "family activities with kids",
        "Ottawa attractions",
        "wine and food experiences",
        "art and culture",
        "water activities"
    ]
    
    for query in test_queries:
        logger.info(f"\n🔎 Searching for: '{query}'")
        results = vector_store.search(query, top_k=5)
        logger.info(f"  Found {len(results)} results")
        
        for i, result in enumerate(results, 1):
            similarity = result.get('similarity_score', 0)
            source = result.get('source', 'unknown')
            title = result.get('title', 'Unknown')
            description = result.get('description', '')[:100] + '...' if result.get('description') else ''
            
            logger.info(f"    {i}. {title}")
            logger.info(f"       Similarity: {similarity:.3f} | Source: {source}")
            if description:
                logger.info(f"       Description: {description}")
    
    return True

def interactive_search():
    """Interactive search mode"""
    logger.info("\n🎯 Interactive Search Mode")
    logger.info("=" * 50)
    
    # Get the vector store instance
    vector_store = get_vector_store()
    
    while True:
        try:
            query = input("\nEnter your search query (or 'quit' to exit): ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            if not query:
                continue
            
            print(f"\n🔎 Searching for: '{query}'")
            results = vector_store.search(query, top_k=5)
            print(f"Found {len(results)} results:")
            
            for i, result in enumerate(results, 1):
                similarity = result.get('similarity_score', 0)
                source = result.get('source', 'unknown')
                title = result.get('title', 'Unknown')
                description = result.get('description', '')
                
                print(f"\n  {i}. {title}")
                print(f"     Similarity: {similarity:.3f} | Source: {source}")
                if description:
                    print(f"     Description: {description}")
                
                # Show location if available
                if result.get('city'):
                    print(f"     Location: {result['city']}")
                if result.get('price_tier'):
                    print(f"     Price Tier: {result['price_tier']}")
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error during search: {e}")
    
    print("\n👋 Goodbye!")

def main():
    """Main function"""
    logger.info("🎯 AI Orchestrator Vector Store Search")
    logger.info("=" * 50)
    
    # First run automated tests
    success = search_existing_vectors()
    
    if success:
        logger.info("\n🎉 Vector store search successful!")
        
        # Ask if user wants interactive mode
        try:
            answer = input("\nWould you like to try interactive search mode? (y/n): ").strip().lower()
            if answer in ['y', 'yes']:
                interactive_search()
        except KeyboardInterrupt:
            pass
    else:
        logger.error("💥 Failed to search vector store")
        sys.exit(1)

if __name__ == "__main__":
    main()