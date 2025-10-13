#!/usr/bin/env python3
"""
Test the agent tools enhanced_web_search function
"""

import asyncio
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from server.tools.agent_tools import enhanced_web_search


async def test_agent_web_search():
    """Test the enhanced_web_search function"""
    
    print("🔍 TESTING AGENT ENHANCED WEB SEARCH")
    print("=" * 50)
    
    # Test the enhanced web search
    result = await enhanced_web_search(
        query="sledding hills",
        location="ottawa"
    )
    
    print(f"Success: {result.get('success')}")
    print(f"Error: {result.get('error', 'None')}")
    print(f"Results found: {result.get('results_found', 0)}")
    
    venues = result.get('results', [])
    print(f"Number of venues: {len(venues)}")
    
    for i, venue in enumerate(venues):
        print(f"\n--- Venue {i+1} ---")
        # Check what fields are available
        for key, value in venue.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(test_agent_web_search())