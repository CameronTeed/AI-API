#!/usr/bin/env python3
"""
Test script to verify that sledding hills query uses comprehensive tool selection
"""

import asyncio
import json
from server.tools.agent_tools import AgentToolsManager


async def test_sledding_comprehensive_search():
    """Test that sledding hills query uses all 5 tools for comprehensive results"""
    
    print("🎿 Testing Sledding Hills Query Comprehensive Tool Selection")
    print("=" * 60)
    
    # Initialize agent tools
    agent = AgentToolsManager()
    
    # Test query
    query = "Find me sledding hills in ottawa"
    
    # Analyze intent
    print(f"📝 Query: {query}")
    print()
    
    intent_result = agent.analyze_query_intent(query)
    print("🧠 Intent Analysis:")
    print(json.dumps(intent_result, indent=2))
    print()
    
    # Check if it recommends all 5 tools
    recommended_tools = intent_result.get('recommended_tools', [])
    expected_tools = [
        'enhanced_web_search',     # Should find blog posts about sledding hills
        'google_places_search',    # Should find official sledding locations  
        'search_date_ideas',       # Should check our database
        'search_featured_dates',   # Should find unique experiences
        'eventbrite_search'        # Should look for sledding events
    ]
    
    print("🔧 Tool Analysis:")
    print(f"   Recommended tools count: {len(recommended_tools)}")
    print(f"   Expected tools count: {len(expected_tools)}")
    print()
    
    print("✅ Tools that SHOULD be used:")
    for tool in expected_tools:
        if tool in recommended_tools:
            print(f"   ✅ {tool} - INCLUDED")
        else:
            print(f"   ❌ {tool} - MISSING")
    print()
    
    if len(recommended_tools) >= 4:  # Should recommend at least 4 tools
        print("🎯 SUCCESS: Query is using comprehensive multi-tool approach!")
        print("   This should find:")
        print("   • Blog posts and articles about sledding in Ottawa (enhanced_web_search)")
        print("   • Official sledding locations and parks (google_places_search)")
        print("   • Curated winter activities in database (search_date_ideas)")
        print("   • Unique sledding experiences (search_featured_dates)")
        print("   • Sledding events and groups (eventbrite_search)")
    else:
        print("⚠️  WARNING: Query is not using comprehensive approach")
        print(f"   Only {len(recommended_tools)} tools recommended")
    
    print()
    print("🔍 Category Analysis:")
    print(f"   Intent: {intent_result.get('intent', 'N/A')}")
    print(f"   Category: {intent_result.get('category', 'N/A')}")
    print(f"   Strategy: {intent_result.get('search_strategy', 'N/A')}")
    print(f"   Location Specific: {intent_result.get('location_specific', False)}")
    

async def test_other_queries():
    """Test other query types to ensure they also get comprehensive treatment"""
    
    print("\n" + "=" * 60)
    print("🎯 Testing Other Query Types")
    print("=" * 60)
    
    agent = AgentToolsManager()
    
    test_queries = [
        "I need date ideas for this weekend",
        "Find romantic restaurants in Ottawa",
        "What outdoor activities can we do tomorrow?",
        "Show me hiking trails near Ottawa"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        intent = agent.analyze_query_intent(query)
        tools = intent.get('recommended_tools', [])
        print(f"   🔧 Tools: {len(tools)} recommended")
        print(f"   📊 Category: {intent.get('category', 'N/A')}")
        if len(tools) >= 4:
            print("   ✅ Comprehensive approach")
        else:
            print("   ⚠️  Limited approach")


if __name__ == "__main__":
    asyncio.run(test_sledding_comprehensive_search())
    asyncio.run(test_other_queries())