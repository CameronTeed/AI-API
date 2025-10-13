#!/usr/bin/env python3
"""
Test to show exactly what happens when enhanced_web_search runs
and debug ScrapingBee/SerpAPI integration
"""

import asyncio
import os
from server.tools.agent_tools import AgentToolsManager
from server.tools.intelligent_crawler import get_intelligent_crawler


async def test_api_keys_and_search():
    """Test API configuration and actual search execution"""
    
    print("🔍 API KEY CONFIGURATION TEST")
    print("=" * 50)
    
    # Check environment variables
    serpapi_key = os.getenv('SERPAPI_API_KEY') or os.getenv('SERPAPI_KEY')
    scrapingbee_key = os.getenv('SCRAPINGBEE_API_KEY')
    
    print(f"SERPAPI_API_KEY: {'✅ SET' if serpapi_key else '❌ MISSING'}")
    if serpapi_key:
        print(f"   Key preview: {serpapi_key[:10]}...")
    
    print(f"SCRAPINGBEE_API_KEY: {'✅ SET' if scrapingbee_key else '❌ MISSING'}")
    if scrapingbee_key:
        print(f"   Key preview: {scrapingbee_key[:10]}...")
    
    print("\n🤖 INTELLIGENT CRAWLER TEST")
    print("=" * 50)
    
    # Test intelligent crawler initialization
    crawler = get_intelligent_crawler()
    print(f"SerpAPI configured: {'✅ YES' if crawler.serpapi_key else '❌ NO - will use DuckDuckGo fallback'}")
    print(f"ScrapingBee configured: {'✅ YES' if crawler.scrapingbee_api_key else '❌ NO - will use basic requests'}")
    
    print("\n🔧 ENHANCED WEB SEARCH TEST")
    print("=" * 50)
    
    # Test enhanced web search
    agent = AgentToolsManager()
    
    print("Testing query: 'sledding hills ottawa'")
    try:
        result = await agent.enhanced_web_search("sledding hills ottawa", city="Ottawa")
        
        print(f"Search success: {result.get('success', False)}")
        
        if result.get('success'):
            results = result.get('results', [])
            print(f"Number of results: {len(results)}")
            
            if results:
                print("\n📄 FIRST RESULT ANALYSIS:")
                first = results[0]
                print(f"   Title: {first.get('title', 'N/A')}")
                print(f"   URL: {first.get('url', 'N/A')}")
                print(f"   Source: {first.get('source', 'N/A')}")
                
                content = first.get('content', '')
                if content:
                    print(f"   Content length: {len(content)} characters")
                    print(f"   Content preview: {content[:150]}...")
                    print("   ✅ CONTENT EXTRACTED - ScrapingBee working!")
                else:
                    print("   ❌ NO CONTENT - ScrapingBee may not be working")
            else:
                print("   ❌ NO RESULTS FOUND")
        else:
            print(f"   ❌ SEARCH FAILED: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"   ❌ EXCEPTION: {e}")
    
    print("\n🌐 DIRECT SERPAPI TEST")
    print("=" * 50)
    
    # Test SerpAPI directly if key is available
    if serpapi_key:
        try:
            search_results = await crawler._serpapi_search("sledding hills", "ottawa")
            
            if search_results:
                print(f"✅ SerpAPI working: {len(search_results)} results")
                if search_results:
                    print(f"   First result: {search_results[0].get('title', 'N/A')}")
                    print(f"   First URL: {search_results[0].get('url', 'N/A')}")
            else:
                print("❌ SerpAPI returned no results")
                
        except Exception as e:
            print(f"❌ SerpAPI error: {e}")
    else:
        print("⚠️ SerpAPI key not configured - using DuckDuckGo fallback")
        
        # Test DuckDuckGo fallback
        try:
            search_results = await crawler._duckduckgo_search("sledding hills", "ottawa")
            if search_results:
                print(f"✅ DuckDuckGo fallback working: {len(search_results)} results")
                if search_results:
                    print(f"   First result: {search_results[0].get('title', 'N/A')}")
            else:
                print("❌ DuckDuckGo fallback returned no results")
        except Exception as e:
            print(f"❌ DuckDuckGo error: {e}")


if __name__ == "__main__":
    asyncio.run(test_api_keys_and_search())