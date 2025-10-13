#!/usr/bin/env python3
"""
Test SerpAPI search functionality directly
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from server.tools.intelligent_crawler import get_intelligent_crawler


async def test_serpapi_search():
    """Test if SerpAPI search is actually working"""
    
    print("🔍 TESTING SERPAPI SEARCH")
    print("=" * 50)
    
    crawler = get_intelligent_crawler()
    
    print(f"SerpAPI key configured: {'YES' if crawler.serpapi_key else 'NO'}")
    
    if crawler.serpapi_key:
        print(f"Key preview: {crawler.serpapi_key[:10]}...")
        
        # Test SerpAPI search directly
        print("\nTesting SerpAPI search for 'sledding hills ottawa'...")
        try:
            results = await crawler._serpapi_search("sledding hills", "ottawa")
            print(f"✅ SerpAPI search successful! Found {len(results)} results")
            
            for i, result in enumerate(results[:3]):
                title = result.get('title', 'No title')
                url = result.get('url', 'No URL')
                print(f"  {i+1}. {title}")
                print(f"     {url}")
                
        except Exception as e:
            print(f"❌ SerpAPI search failed: {e}")
    
    # Now test the full intelligent search
    print(f"\nTesting full intelligent search...")
    try:
        result = await crawler.intelligent_search_and_extract(
            query="sledding hills", 
            city="ottawa",
            max_results=3
        )
        
        print(f"Search successful: {result.get('success', False)}")
        print(f"Results found: {result.get('results_found', 0)}")
        venues = result.get('venues', [])
        
        if venues:
            print(f"\nFound venues:")
            for venue in venues[:3]:
                print(f"  • {venue.get('title', 'No title')}")
                print(f"    {venue.get('url', 'No URL')}")
        else:
            print("No venues returned")
            
    except Exception as e:
        print(f"❌ Full search failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_serpapi_search())