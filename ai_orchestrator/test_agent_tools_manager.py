#!/usr/bin/env python3
"""
Test the AgentToolsManager enhanced_web_search
"""

import asyncio
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from server.tools.agent_tools import AgentToolsManager


async def test_agent_tools_manager():
    """Test the AgentToolsManager enhanced_web_search"""
    
    print("🔍 TESTING AGENT TOOLS MANAGER")
    print("=" * 50)
    
    # Create the tools manager
    tools_manager = AgentToolsManager()
    
    # Test the enhanced web search
    result = await tools_manager.enhanced_web_search(
        query="sledding hills",
        city="ottawa"
    )
    
    print(f"Success: {result.get('success')}")
    print(f"Error: {result.get('error', 'None')}")
    print(f"Result keys: {list(result.keys())}")
    
    items = result.get('items', [])
    venues = result.get('venues', [])
    results = result.get('results', [])
    
    print(f"Items found: {len(items)}")
    print(f"Venues found: {len(venues)}")
    print(f"Results found: {len(results)}")
    
    # Show items if any
    for i, item in enumerate(items[:3]):
        print(f"\n--- Item {i+1} ---")
        for key, value in item.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
    
    # Show venues if any
    for i, venue in enumerate(venues[:3]):
        print(f"\n--- Venue {i+1} ---")
        for key, value in venue.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(test_agent_tools_manager())