#!/usr/bin/env python3
"""
Test the enhanced extraction with multiple fallback methods
"""

import asyncio
import time
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from server.tools.intelligent_crawler import get_intelligent_crawler


async def test_enhanced_extraction():
    """Test the enhanced extraction with multiple fallback methods"""
    
    print("🚀 TESTING ENHANCED EXTRACTION WITH FALLBACKS")
    print("=" * 60)
    
    crawler = get_intelligent_crawler()
    
    # Test with a known sledding URL that should have content
    test_urls = [
        "https://ottawaisnotboring.com/2021/02/02/__trashed-8/",  # Known sledding article
        "https://open.ottawa.ca/datasets/sledding-hills"  # Government data
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n🔍 Test {i}: {url}")
        print("-" * 40)
        
        start_time = time.time()
        
        result = await crawler.extract_venue_information(
            url,
            venue_name=f"Test Sledding Location {i}"
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️ Extraction time: {duration:.1f} seconds")
        print(f"Success: {result.get('success', False)}")
        
        if result.get('success'):
            data = result.get('data', {})
            extraction_method = result.get('extraction_method', 'unknown')
            
            print(f"✅ Method used: {extraction_method}")
            print(f"Venue name: {data.get('venue_name', 'N/A')}")
            print(f"Description length: {len(data.get('description', ''))}")
            
            # Check sledding-specific info
            sledding_info = data.get('sledding_specific', {})
            hills = sledding_info.get('hills_mentioned', [])
            locations = sledding_info.get('locations', [])
            
            print(f"🎿 Sledding hills found: {len(hills)}")
            if hills:
                for hill in hills[:3]:
                    print(f"   • {hill}")
            
            print(f"📍 Locations mentioned: {locations}")
            
            # Show some content
            description = data.get('description', '')
            if description:
                print(f"📝 Description preview: {description[:200]}...")
        else:
            print(f"❌ Extraction failed: {result.get('error', 'Unknown error')}")
    
    print(f"\n🏁 Enhanced extraction test completed!")


if __name__ == "__main__":
    asyncio.run(test_enhanced_extraction())