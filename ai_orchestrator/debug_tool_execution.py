#!/usr/bin/env python3
"""
Debug script to investigate why tools are returning "no results"
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

async def debug_tool_execution():
    """Debug individual tool execution"""
    print("🐛 Debugging Individual Tool Execution")
    print("=" * 50)
    
    # Initialize tools manager
    tools_manager = AgentToolsManager()
    # No need to call initialize() - it's done in __init__
    
    query = "Find me cooking classes in ottawa"
    city = "Ottawa"
    
    print(f"📝 Query: {query}")
    print(f"🏙️ City: {city}")
    print()
    
    # Test each tool individually
    tools_to_test = [
        ('eventbrite_search', {}),
        ('enhanced_web_search', {}),
        ('google_places_search', {})
    ]
    
    for tool_name, extra_kwargs in tools_to_test:
        print(f"🔧 Testing {tool_name}...")
        print("-" * 30)
        
        try:
            # Get the tool method
            tool_method = getattr(tools_manager, tool_name, None)
            if not tool_method:
                print(f"❌ Tool {tool_name} not found")
                continue
            
            # Execute the tool
            kwargs = {'query': query, 'city': city, **extra_kwargs}
            result = await tool_method(**kwargs)
            
            print(f"📊 Result structure:")
            print(f"   - success: {result.get('success', 'not set')}")
            print(f"   - items count: {len(result.get('items', []))}")
            print(f"   - error: {result.get('error', 'none')}")
            print(f"   - source: {result.get('source', 'not set')}")
            
            # Show first few items
            items = result.get('items', [])
            if items:
                print(f"📝 First item preview:")
                first_item = items[0]
                print(f"   - title: {first_item.get('title', 'N/A')[:80]}...")
                print(f"   - source: {first_item.get('source', 'N/A')}")
                if 'url' in first_item:
                    print(f"   - url: {first_item['url'][:60]}...")
            else:
                print(f"⚠️  No items returned")
            
            print()
            
        except Exception as e:
            print(f"❌ Error testing {tool_name}: {e}")
            print()
    
    print("🔍 Testing tool execution logic...")
    print("-" * 30)
    
    # Test the specific execution logic that checks for "no results"
    test_results = [
        {"success": True, "items": [{"title": "test"}]},  # Should pass
        {"success": True, "items": []},  # Should fail - no items
        {"success": False, "items": [{"title": "test"}]},  # Should fail - not successful
        {"items": [{"title": "test"}]},  # Should pass - no success key defaults to True
        {"items": []},  # Should fail - no items
        {},  # Should fail - no items
    ]
    
    for i, result in enumerate(test_results):
        success = result.get("success", True)
        items = result.get("items", [])
        has_results = success and items
        print(f"Test {i+1}: success={success}, items={len(items)} -> passes={has_results}")

if __name__ == "__main__":
    asyncio.run(debug_tool_execution())