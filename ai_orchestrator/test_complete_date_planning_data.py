#!/usr/bin/env python3
"""
Test complete date-planning data structure for LLM synthesis
"""

import asyncio
import json
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from server.tools.agent_tools import AgentToolsManager


async def test_complete_date_planning_data():
    """Test the complete date-planning data structure"""
    
    print("💕 TESTING COMPLETE DATE-PLANNING DATA")
    print("=" * 60)
    
    tools_manager = AgentToolsManager()
    
    # Test enhanced web search for sledding
    result = await tools_manager.enhanced_web_search(
        query="sledding hills",
        city="ottawa"
    )
    
    print(f"Search Success: {result.get('success')}")
    
    items = result.get('items', [])
    print(f"Found {len(items)} venues with enhanced data")
    
    for i, item in enumerate(items[:1], 1):  # Just show first one for detail
        print(f"\n{'='*20} VENUE {i} - DATE PLANNING DATA {'='*20}")
        print(f"Title: {item.get('title', 'N/A')}")
        print(f"URL: {item.get('url', 'N/A')}")
        
        # Show all the date-planning relevant fields
        print(f"\n📝 BASIC INFO:")
        print(f"  Description: {item.get('description', 'N/A')[:100]}...")
        print(f"  Phone: {item.get('phone', 'N/A')}")
        print(f"  Address: {item.get('address', 'N/A')}")
        print(f"  Hours: {item.get('hours', 'N/A')}")
        
        print(f"\n💰 PRICING:")
        pricing = item.get('pricing_info', {})
        print(f"  Pricing Info: {pricing}")
        print(f"  Price Mentions: {item.get('price_mentions', [])}")
        
        print(f"\n📅 EVENTS & HIGHLIGHTS:")
        print(f"  Events: {len(item.get('events', []))} found")
        print(f"  Highlights: {len(item.get('highlights', []))} found")
        for highlight in item.get('highlights', [])[:2]:
            print(f"    • {highlight[:80]}...")
        
        # Show the full item structure for LLM analysis
        print(f"\n🤖 FULL DATA STRUCTURE FOR LLM:")
        print("```json")
        print(json.dumps(item, indent=2)[:2000] + "..." if len(json.dumps(item)) > 2000 else json.dumps(item, indent=2))
        print("```")
    
    print(f"\n💕 This rich data helps the LLM create perfect date recommendations!")
    
    # Show what the LLM will see for date planning
    print(f"\n🎯 KEY DATE-PLANNING INSIGHTS FROM DATA:")
    if items:
        item = items[0]
        insights = []
        
        if item.get('price_mentions'):
            if 'free' in str(item.get('price_mentions')).lower():
                insights.append("✅ Budget-friendly (free activity)")
        
        if 'family' in item.get('description', '').lower():
            insights.append("✅ Family-friendly atmosphere")
            
        if any(word in item.get('description', '').lower() for word in ['scenic', 'beautiful', 'view']):
            insights.append("✅ Scenic/romantic potential")
            
        if item.get('phone') or item.get('address'):
            insights.append("✅ Easy to contact/locate")
            
        if item.get('highlights'):
            insights.append(f"✅ {len(item.get('highlights', []))} unique features highlighted")
        
        for insight in insights:
            print(f"  {insight}")


if __name__ == "__main__":
    asyncio.run(test_complete_date_planning_data())