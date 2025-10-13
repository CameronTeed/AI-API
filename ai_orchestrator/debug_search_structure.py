#!/usr/bin/env python3
"""
Debug the exact search result structure and extraction fallback
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from server.tools.intelligent_crawler import get_intelligent_crawler


async def debug_search_structure():
    """Debug the search result structure and extraction fallback"""
    
    print("🔍 DEBUGGING SEARCH RESULT STRUCTURE")
    print("=" * 60)
    
    crawler = get_intelligent_crawler()
    
    # Get raw search results
    print("Step 1: Raw SerpAPI results...")
    raw_results = await crawler._serpapi_search("sledding hills", "ottawa")
    
    for i, result in enumerate(raw_results[:3]):
        print(f"\nRaw result {i+1}:")
        for key, value in result.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
    
    print(f"\nStep 2: URL Info Processing...")
    # Check how URLs are processed
    relevant_urls = [
        {
            'url': result['url'],
            'title': result['title'], 
            'snippet': result.get('snippet', '')
        }
        for result in raw_results 
        if crawler._is_relevant_url(result['url'], "sledding hills")
    ]
    
    print(f"Found {len(relevant_urls)} relevant URLs:")
    for i, url_info in enumerate(relevant_urls[:3]):
        print(f"\nURL Info {i+1}:")
        print(f"  URL: {url_info['url']}")
        print(f"  Title: {url_info['title']}")
        print(f"  Snippet: {url_info['snippet'][:100]}...")
    
    print(f"\nStep 3: Test extraction on one URL...")
    if relevant_urls:
        test_url = relevant_urls[0]
        print(f"Testing extraction for: {test_url['title']}")
        
        try:
            extracted = await crawler.extract_venue_information(
                test_url['url'],
                venue_name=test_url['title']
            )
            
            print(f"Extraction success: {extracted.get('success')}")
            if not extracted.get('success'):
                print(f"Extraction error: {extracted.get('error')}")
                
                # Show what the fallback data should be
                fallback_data = {
                    'venue_name': test_url['title'],
                    'url': test_url['url'],
                    'description': test_url['snippet'],
                    'source': 'search_only',
                    'extraction_error': extracted.get('error', 'Unknown error')
                }
                
                print(f"Fallback data would be:")
                for key, value in fallback_data.items():
                    print(f"  {key}: {value}")
                    
        except Exception as e:
            print(f"Extraction exception: {e}")


if __name__ == "__main__":
    asyncio.run(debug_search_structure())