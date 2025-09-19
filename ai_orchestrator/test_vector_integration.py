#!/usr/bin/env python3
"""
Test script to verify the vector store integration works properly.
"""
import asyncio
import os
import sys
import logging
import json

# Add the current directory to the path so we can import from server
sys.path.insert(0, os.path.dirname(__file__))

from server.tools.vector_store import get_vector_store
from server.llm.engine import LLMEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_vector_store():
    """Test the vector store functionality"""
    logger.info("Testing vector store...")
    
    # Get vector store instance
    vector_store = get_vector_store()
    
    # Check stats
    stats = vector_store.get_stats()
    logger.info(f"Vector store stats: {stats}")
    
    if stats['total_date_ideas'] == 0:
        logger.warning("No date ideas in vector store. Run populate_vector_store.py first.")
        return False
    
    # Test search
    test_queries = [
        "romantic dinner for two",
        "outdoor adventure",
        "fun indoor activities",
        "wine tasting experience",
        "family-friendly activities"
    ]
    
    for query in test_queries:
        logger.info(f"Testing search: '{query}'")
        results = vector_store.search(query, top_k=3)
        logger.info(f"  Found {len(results)} results")
        
        for i, result in enumerate(results, 1):
            logger.info(f"    {i}. {result['title']} (score: {result.get('similarity_score', 0):.3f})")
    
    return True

async def test_llm_integration():
    """Test the LLM integration with vector store"""
    logger.info("Testing LLM integration...")
    
    # Mock functions for testing
    vector_store = get_vector_store()
    
    async def mock_vector_search(**kwargs):
        """Mock vector search function"""
        results = vector_store.search(**kwargs)
        return {"items": results, "source": "vector_store"}
    
    async def mock_web_search(**kwargs):
        """Mock web search function"""
        return {"items": [], "source": "web"}
    
    # Create LLM engine
    if not os.getenv('OPENAI_API_KEY'):
        logger.warning("OPENAI_API_KEY not set. Skipping LLM test.")
        return True
    
    llm_engine = LLMEngine()
    
    # Test message
    messages = [
        {"role": "user", "content": "I want a romantic date idea in New York for under $50"}
    ]
    
    logger.info("Testing LLM chat with vector store...")
    try:
        full_response = ""
        async for chunk in llm_engine.run_chat(
            messages=messages,
            vector_search_func=mock_vector_search,
            web_search_func=mock_web_search
        ):
            full_response += chunk
        
        logger.info(f"LLM response received (length: {len(full_response)})")
        logger.info(f"Response preview: {full_response[:200]}...")
        return True
        
    except Exception as e:
        logger.error(f"LLM test failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("Starting vector store integration tests...")
    
    # Test vector store
    vector_store_ok = await test_vector_store()
    
    # Test LLM integration
    llm_ok = await test_llm_integration()
    
    if vector_store_ok and llm_ok:
        logger.info("✅ All tests passed! Vector store integration is working.")
    else:
        logger.error("❌ Some tests failed. Check the logs above.")
    
    return vector_store_ok and llm_ok

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
