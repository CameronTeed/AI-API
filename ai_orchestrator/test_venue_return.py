#!/usr/bin/env python3
"""
Test exactly what the intelligent search returns for venues
"""

import asyncio
import json
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from server.tools.intelligent_crawler import get_intelligent_crawler


async def test_venue_return():
    """Test exactly what venue data is returned"""
    
    print("🔍 TESTING VENUE RETURN DATA")
    print("=" * 50)
    
    crawler = get_intelligent_crawler()
    
    # Test the full intelligent search
    result = await crawler.intelligent_search_and_extract(
        query="sledding hills", 
        city="ottawa",
        max_results=3
    )
    
    print("Full result keys:", result.keys())
    print(f"Success: {result.get('success')}")
    print(f"Results found: {result.get('results_found')}")
    
    venues = result.get('venues', [])
    print(f"Number of venues: {len(venues)}")
    
    for i, venue in enumerate(venues):
        print(f"\n--- Venue {i+1} ---")
        print(json.dumps(venue, indent=2))
        
        # Check specifically for title fields
        title_fields = ['title', 'venue_name', 'search_title']
        for field in title_fields:
            if field in venue:
                print(f"  {field}: '{venue[field]}'")


if __name__ == "__main__":
    asyncio.run(test_venue_return())