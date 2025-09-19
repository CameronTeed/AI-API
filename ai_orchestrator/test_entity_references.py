#!/usr/bin/env python3
"""
Test script to verify entity references work properly.
"""
import os
import sys
import json
import logging

# Add the current directory to the path so we can import from server
sys.path.insert(0, os.path.dirname(__file__))

from server.tools.vector_store import get_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_entity_references():
    """Test that entity references are properly built"""
    logger.info("Testing entity references...")
    
    # Get vector store instance
    vector_store = get_vector_store()
    
    # Check if we have data
    stats = vector_store.get_stats()
    if stats['total_date_ideas'] == 0:
        logger.warning("No date ideas in vector store. Run populate_vector_store.py first.")
        return False
    
    # Test search with entity references
    results = vector_store.search("romantic dinner", top_k=2)
    
    if not results:
        logger.error("No search results returned")
        return False
    
    logger.info(f"Found {len(results)} results")
    
    for i, result in enumerate(results, 1):
        logger.info(f"\n--- Result {i}: {result['title']} ---")
        
        # Check if entity_references exists
        if "entity_references" not in result:
            logger.error(f"Missing entity_references in result {i}")
            return False
        
        entity_refs = result["entity_references"]
        
        # Check primary entity
        primary = entity_refs.get("primary_entity")
        if not primary:
            logger.error(f"Missing primary_entity in result {i}")
            return False
        
        logger.info(f"Primary Entity: {primary['type']} - {primary['title']} ({primary['id']})")
        if primary.get('url'):
            logger.info(f"  URL: {primary['url']}")
        
        # Check related entities
        related = entity_refs.get("related_entities", [])
        logger.info(f"Related Entities ({len(related)}):")
        
        for entity in related:
            logger.info(f"  - {entity['type']}: {entity['title']} ({entity['id']})")
            if entity.get('url'):
                logger.info(f"    URL: {entity['url']}")
        
        # Verify required entity types are present
        entity_types = {entity['type'] for entity in related}
        expected_types = {'city', 'price_tier'}
        
        for expected_type in expected_types:
            if expected_type not in entity_types:
                logger.warning(f"Expected entity type '{expected_type}' not found in result {i}")
    
    logger.info("✅ Entity references test completed successfully!")
    return True

def test_json_serialization():
    """Test that entity references serialize properly to JSON"""
    logger.info("Testing JSON serialization...")
    
    vector_store = get_vector_store()
    results = vector_store.search("wine tasting", top_k=1)
    
    if not results:
        logger.error("No results for JSON test")
        return False
    
    result = results[0]
    
    try:
        # Try to serialize to JSON
        json_str = json.dumps(result, indent=2, default=str)
        logger.info("JSON serialization successful")
        
        # Try to deserialize
        parsed = json.loads(json_str)
        
        # Verify entity references are preserved
        if "entity_references" not in parsed:
            logger.error("entity_references lost in JSON serialization")
            return False
        
        logger.info("✅ JSON serialization test passed!")
        return True
        
    except Exception as e:
        logger.error(f"JSON serialization failed: {e}")
        return False

def main():
    """Run all entity reference tests"""
    logger.info("Starting entity reference tests...")
    
    # Test entity references
    refs_ok = test_entity_references()
    
    # Test JSON serialization
    json_ok = test_json_serialization()
    
    if refs_ok and json_ok:
        logger.info("🎉 All entity reference tests passed!")
        logger.info("\nNext steps:")
        logger.info("1. Frontend can now render clickable keywords using entity_references")
        logger.info("2. Each entity has id, type, title, and url for navigation")
        logger.info("3. Primary entity is the main date idea")
        logger.info("4. Related entities include venues, cities, categories, etc.")
    else:
        logger.error("❌ Some entity reference tests failed")
    
    return refs_ok and json_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
