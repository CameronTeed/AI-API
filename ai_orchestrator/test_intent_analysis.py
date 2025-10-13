#!/usr/bin/env python3
"""
Test the intent analysis for 'Find me sledding hills in ottawa'
"""

import asyncio
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from server.tools.agent_tools import AgentToolsManager


async def test_intent_analysis():
    """Test if sledding query gets 5-tool treatment"""
    
    print("🎯 TESTING INTENT ANALYSIS")
    print("=" * 50)
    
    # Create tools manager
    tools_manager = AgentToolsManager()
    
    # Test queries
    test_queries = [
        "Find me sledding hills in ottawa",
        "sledding hills ottawa", 
        "Where can I go sledding in Ottawa?",
        "Ottawa toboggan hills",
        "Best places for sledding near me",
        "Find restaurants in Ottawa",  # Control - should not get 5 tools
        "Coffee shops downtown"  # Control - should not get 5 tools
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        
        # Test intent analysis
        intent = tools_manager.analyze_query_intent(query)
        
        print(f"  Intent category: {intent.get('category', 'unknown')}")
        print(f"  Use enhanced search: {intent.get('use_enhanced_search', False)}")
        
        # Check recommended tools
        recommended_tools = intent.get('recommended_tools', [])
        print(f"  Recommended tools ({len(recommended_tools)}): {recommended_tools}")
        
        # Check if it meets 5-tool criteria
        if len(recommended_tools) >= 4:  # Allow some flexibility
            print(f"  ✅ GOOD: Comprehensive search with {len(recommended_tools)} tools")
        elif len(recommended_tools) >= 2:
            print(f"  ⚠️ MODERATE: Standard search with {len(recommended_tools)} tools")
        else:
            print(f"  ❌ LIMITED: Basic search with {len(recommended_tools)} tools")
        
        # Check for outdoor activity detection
        if 'outdoor' in intent.get('category', '').lower() or any('outdoor' in tool for tool in recommended_tools):
            print(f"  🏔️ Detected as outdoor activity")


if __name__ == "__main__":
    asyncio.run(test_intent_analysis())