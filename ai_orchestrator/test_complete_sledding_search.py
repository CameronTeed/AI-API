#!/usr/bin/env python3
"""
Test complete end-to-end sledding search with enhanced extraction
"""

import asyncio
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from server.tools.intelligent_crawler import get_intelligent_crawler


async def test_complete_sledding_search():
    """Test complete sledding search with enhanced extraction"""
    
    print("🎿 TESTING COMPLETE SLEDDING SEARCH")
    print("=" * 60)
    
    crawler = get_intelligent_crawler()
    
    # Test the exact query the user mentioned
    result = await crawler.intelligent_search_and_extract(
        query="sledding hills", 
        city="ottawa",
        max_results=2  # Just test 2 for speed
    )
    
    print(f"Search Success: {result.get('success')}")
    print(f"Results Found: {result.get('results_found', 0)}")
    
    venues = result.get('venues', [])
    
    for i, venue in enumerate(venues, 1):
        print(f"\n{'='*20} VENUE {i} {'='*20}")
        print(f"Name: {venue.get('venue_name', 'N/A')}")
        print(f"URL: {venue.get('url', 'N/A')}")
        print(f"Source: {venue.get('source', 'N/A')}")
        print(f"Extraction Method: {venue.get('extraction_method', 'N/A')}")
        
        description = venue.get('description', '')
        if description:
            print(f"Description ({len(description)} chars): {description[:200]}...")
        
        # Show sledding-specific info
        sledding_info = venue.get('sledding_specific', {})
        if sledding_info:
            hills = sledding_info.get('hills_mentioned', [])
            locations = sledding_info.get('locations', [])
            safety = sledding_info.get('safety_info', [])
            features = sledding_info.get('features', [])
            
            if hills:
                print(f"🏔️ Hills Mentioned ({len(hills)}): {hills[:5]}")
            if locations:
                print(f"📍 Locations: {locations}")
            if safety:
                print(f"🛡️ Safety Info: {safety[0] if safety else 'None'}")
            if features:
                print(f"🎯 Features: {features[:3]}")
        
        # Show other extracted data
        contact = venue.get('contact', {})
        if contact and any(contact.values()):
            print(f"📞 Contact: {contact}")
        
        events = venue.get('events', [])
        if events:
            print(f"📅 Events: {len(events)} found")
    
    print(f"\n🏁 Complete sledding search test finished!")
    print(f"🎯 This is exactly the rich content users will now get!")


if __name__ == "__main__":
    asyncio.run(test_complete_sledding_search())