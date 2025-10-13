#!/usr/bin/env python3
"""
Test the optimized intelligent crawler with faster timeouts
"""

import asyncio
import time
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from server.tools.intelligent_crawler import get_intelligent_crawler


async def test_optimized_crawler():
    """Test the optimized crawler with reduced timeouts"""
    
    print("🚀 TESTING OPTIMIZED CRAWLER")
    print("=" * 50)
    
    crawler = get_intelligent_crawler()
    
    # Test with the exact query that was timing out
    start_time = time.time()
    
    result = await crawler.intelligent_search_and_extract(
        query="sledding hills", 
        city="ottawa",
        max_results=2  # Even fewer results for faster testing
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"⏱️ Total execution time: {duration:.1f} seconds")
    print(f"Success: {result.get('success')}")
    print(f"Results found: {result.get('results_found', 0)}")
    
    venues = result.get('venues', [])
    if venues:
        print(f"\nFound venues:")
        for venue in venues:
            title = venue.get('venue_name', 'No title')
            url = venue.get('url', 'No URL')
            source = venue.get('source', 'unknown')
            print(f"  • {title} ({source})")
            print(f"    {url}")
    
    # Performance analysis
    if duration < 30:
        print(f"✅ GOOD: Completed in {duration:.1f}s (under 30s target)")
    elif duration < 60:
        print(f"⚠️ ACCEPTABLE: Completed in {duration:.1f}s (under 1 minute)")
    else:
        print(f"❌ SLOW: Took {duration:.1f}s (over 1 minute)")


if __name__ == "__main__":
    asyncio.run(test_optimized_crawler())