#!/usr/bin/env python3
"""
Test the enhanced date-planning extraction features
"""

import asyncio
import json
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from server.tools.intelligent_crawler import get_intelligent_crawler


async def test_date_planning_extraction():
    """Test the enhanced date-planning extraction"""
    
    print("💕 TESTING DATE-PLANNING EXTRACTION")
    print("=" * 60)
    
    crawler = get_intelligent_crawler()
    
    # Test with sledding URL that should have rich content
    test_url = "https://ottawaisnotboring.com/2021/02/02/__trashed-8/"
    
    print(f"Testing: {test_url}")
    print("-" * 40)
    
    result = await crawler.extract_venue_information(
        test_url,
        venue_name="Ottawa Sledding Guide"
    )
    
    if result.get('success'):
        data = result.get('data', {})
        
        print(f"✅ Extraction successful using: {result.get('extraction_method')}")
        print(f"Venue: {data.get('venue_name', 'N/A')}")
        
        # Display date-planning specific information
        sledding_info = data.get('sledding_specific', {})
        date_planning = data.get('date_planning', {})
        images = data.get('images', {})
        
        print(f"\n💕 DATE SUITABILITY:")
        date_suit = sledding_info.get('date_suitability', {})
        print(f"  Romantic Factor: {date_suit.get('romantic_factor', 0)}/5")
        print(f"  Couple Friendly: {date_suit.get('couple_friendly', False)}")
        print(f"  Scenic Views: {date_suit.get('scenic_views', False)}")
        print(f"  Instagram Worthy: {date_suit.get('instagram_worthy', False)}")
        
        print(f"\n🚗 LOGISTICS:")
        logistics = sledding_info.get('logistics', {})
        parking = logistics.get('parking', [])
        amenities = logistics.get('nearby_amenities', [])
        if parking:
            print(f"  Parking: {parking[0][:100]}...")
        if amenities:
            print(f"  Amenities: {len(amenities)} mentions")
            for amenity in amenities[:2]:
                print(f"    • {amenity[:80]}...")
        
        print(f"\n💰 COST INFO:")
        cost_info = sledding_info.get('cost_info', {})
        print(f"  Free: {cost_info.get('free', False)}")
        print(f"  Equipment Rental: {cost_info.get('equipment_rental', False)}")
        cost_mentions = cost_info.get('cost_mentions', [])
        if cost_mentions:
            print(f"  Cost Mentions: {cost_mentions}")
        
        print(f"\n📸 IMAGES:")
        print(f"  Featured Images: {len(images.get('featured_images', []))}")
        print(f"  Gallery Images: {len(images.get('gallery_images', []))}")
        if images.get('featured_images'):
            print(f"  Sample: {images['featured_images'][0]}")
        
        print(f"\n🌟 ATMOSPHERE:")
        atmosphere = date_planning.get('atmosphere', {})
        for key, value in atmosphere.items():
            print(f"  {key.title()}: {value}")
        
        print(f"\n⏰ TIMING & LOGISTICS:")
        best_times = sledding_info.get('best_times', [])
        if best_times:
            print(f"  Best Times: {best_times[0][:100]}...")
        
        memorable = date_planning.get('memorable_aspects', [])
        if memorable:
            print(f"  Memorable: {memorable[0][:100]}...")
        
        print(f"\n🎯 UNIQUE FEATURES:")
        unique = sledding_info.get('unique_features', [])
        for feature in unique[:2]:
            print(f"  • {feature[:100]}...")
        
    else:
        print(f"❌ Extraction failed: {result.get('error')}")
    
    print(f"\n💕 Date planning extraction test complete!")


if __name__ == "__main__":
    asyncio.run(test_date_planning_extraction())