#!/usr/bin/env python3
"""
Debug exactly what happens during URL filtering and result processing
"""

import asyncio
from server.tools.intelligent_crawler import get_intelligent_crawler


async def debug_url_filtering():
    """Debug the URL filtering and result processing step by step"""
    
    print("🔍 DETAILED URL FILTERING DEBUG")
    print("=" * 60)
    
    crawler = get_intelligent_crawler()
    
    # Step 1: Get search results
    print("Step 1: Getting search results...")
    search_results = await crawler._serpapi_search("sledding hills", "ottawa")
    print(f"Found {len(search_results)} search results")
    
    # Step 2: Show all results and filtering decisions
    print("\nStep 2: URL Filtering Analysis:")
    for i, result in enumerate(search_results[:5]):
        url = result.get('url', '')
        title = result.get('title', '')
        
        print(f"\n   Result {i+1}:")
        print(f"   Title: {title}")
        print(f"   URL: {url}")
        
        # Test filtering
        is_relevant = crawler._is_relevant_url(url, "sledding hills")
        print(f"   Filtering decision: {'✅ ACCEPTED' if is_relevant else '❌ REJECTED'}")
    
    # Step 3: Test intelligent search 
    print(f"\nStep 3: Full intelligent search test...")
    result = await crawler.intelligent_search_and_extract(
        query="sledding hills",
        city="ottawa", 
        max_results=3
    )
    
    print(f"Search success: {result.get('success', False)}")
    print(f"Results found: {result.get('results_found', 0)}")
    venues = result.get('venues', [])
    print(f"Venues returned: {len(venues)}")
    
    if venues:
        print("\n📋 VENUE DETAILS:")
        for i, venue in enumerate(venues[:2]):
            print(f"   Venue {i+1}:")
            print(f"      Name: {venue.get('venue_name', 'N/A')}")  
            print(f"      URL: {venue.get('url', 'N/A')}")
            print(f"      Source: {venue.get('source', 'N/A')}")
            description = venue.get('description', '')
            if description:
                print(f"      Description: {description[:100]}...")
    else:
        print("   ❌ No venues returned")
        
        # Check if URLs were filtered out
        print("\n🔍 DIAGNOSIS:")
        relevant_urls = [r['url'] for r in search_results[:5] if crawler._is_relevant_url(r['url'], "sledding hills")]
        print(f"   URLs that passed filtering: {len(relevant_urls)}")
        for url in relevant_urls[:3]:
            print(f"      ✅ {url}")
            
        if len(relevant_urls) == 0:
            print("   🚨 PROBLEM: All URLs were filtered out!")
        else:
            print("   🚨 PROBLEM: URLs passed filtering but scraping failed!")


if __name__ == "__main__":
    asyncio.run(debug_url_filtering())