#!/usr/bin/env python3
"""
Test the simplified ScrapingBee method directly
"""

import asyncio
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from server.tools.intelligent_crawler import get_intelligent_crawler


async def test_simplified_scrapingbee():
    """Test the simplified ScrapingBee method"""
    
    print("🚀 TESTING SIMPLIFIED SCRAPINGBEE")
    print("=" * 50)
    
    crawler = get_intelligent_crawler()
    
    test_url = "https://ottawaisnotboring.com/2021/02/02/__trashed-8/"
    
    print(f"Testing: {test_url}")
    
    # Test simplified scraping directly
    print("Trying simplified ScrapingBee (no JS)...")
    content = await crawler._scrape_simplified(test_url)
    
    if content:
        print(f"✅ Simplified ScrapingBee successful!")
        print(f"Content length: {len(content)}")
        print(f"Content preview: {content[:300]}...")
        
        # Test if we can find sledding content
        if 'sledding' in content.lower() or 'toboggan' in content.lower():
            print("🎿 Found sledding content!")
        else:
            print("⚠️ No sledding content found")
    else:
        print("❌ Simplified ScrapingBee also failed")


if __name__ == "__main__":
    asyncio.run(test_simplified_scrapingbee())