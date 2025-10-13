#!/usr/bin/env python3
"""
Test the enhanced content extraction specifically
"""
import asyncio
import sys
import os
import logging

# Add the parent directory to the path so we can import server modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server.tools.agent_tools import AgentToolsManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_content_extraction():
    """Test content extraction from specific sources"""
    print("🕷️ Testing Enhanced Content Extraction")
    print("=" * 50)
    
    # Initialize tools manager
    tools_manager = AgentToolsManager()
    
    query = "Find me cooking classes in ottawa"
    
    print(f"📝 Query: {query}")
    print()
    
    # Test enhanced web search specifically
    print("🌐 Testing Enhanced Web Search...")
    print("-" * 30)
    
    web_results = await tools_manager.enhanced_web_search(query)
    
    print(f"📊 Web Search Results:")
    print(f"   - Success: {web_results.get('success')}")
    print(f"   - Items: {len(web_results.get('items', []))}")
    
    for i, item in enumerate(web_results.get('items', [])[:2]):
        print(f"\n🔍 Item {i+1}:")
        print(f"   - Title: {item.get('title', 'N/A')[:80]}...")
        print(f"   - URL: {item.get('url', 'N/A')[:80]}...")
        print(f"   - Basic snippet: {item.get('snippet', 'N/A')[:100]}...")
        
        # Check for enhanced content
        if item.get('full_description'):
            print(f"   - ✅ Full description: {item.get('full_description')[:150]}...")
        else:
            print(f"   - ❌ No full description extracted")
            
        if item.get('contact_info'):
            print(f"   - ✅ Contact info: {item.get('contact_info')}")
        else:
            print(f"   - ❌ No contact info extracted")
            
        if item.get('address'):
            print(f"   - ✅ Address: {item.get('address')}")
        else:
            print(f"   - ❌ No address extracted")
            
        if item.get('pricing_info'):
            print(f"   - ✅ Pricing: {item.get('pricing_info')}")
        else:
            print(f"   - ❌ No pricing info extracted")
    
    print("\n" + "="*50)
    
    # Test Eventbrite search specifically
    print("🎫 Testing Enhanced Eventbrite Search...")
    print("-" * 30)
    
    eventbrite_results = await tools_manager.eventbrite_search(query, "Ottawa")
    
    print(f"📊 Eventbrite Results:")
    print(f"   - Success: {eventbrite_results.get('success')}")
    print(f"   - Items: {len(eventbrite_results.get('items', []))}")
    
    for i, item in enumerate(eventbrite_results.get('items', [])[:2]):
        print(f"\n🎫 Item {i+1}:")
        print(f"   - Title: {item.get('title', 'N/A')[:80]}...")
        print(f"   - Description: {item.get('description', 'N/A')[:150]}...")
        print(f"   - Event type: {item.get('event_type', 'N/A')}")
        
        if item.get('venue') and item.get('venue') != 'Various venues':
            print(f"   - ✅ Venue: {item.get('venue')}")
        else:
            print(f"   - ❌ No specific venue info")
            
        if item.get('price') and item.get('price') != 'Various prices':
            print(f"   - ✅ Price: {item.get('price')}")
        else:
            print(f"   - ❌ No specific price info")
            
        if item.get('date') and item.get('date') != 'Various dates':
            print(f"   - ✅ Date: {item.get('date')}")
        else:
            print(f"   - ❌ No specific date info")

if __name__ == "__main__":
    asyncio.run(test_content_extraction())