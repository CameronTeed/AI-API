#!/usr/bin/env python3
"""
Debug script to show exactly what each tool returns and why synthesis chooses certain results
"""
import asyncio
import sys
import os
import logging

# Add the parent directory to the path so we can import server modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server.tools.agent_tools import AgentToolsManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_synthesis_input():
    """Debug what data goes into the synthesis"""
    print("🔍 Debugging Synthesis Input Data")
    print("=" * 50)
    
    # Initialize tools manager
    tools_manager = AgentToolsManager()
    
    query = "Find me cooking classes in ottawa"
    
    # Create execution plan first
    plan = await tools_manager.create_execution_plan(query, None)
    
    # Execute the full plan to get all results
    execution_results = await tools_manager.execute_plan(plan, query, None)
    
    print(f"📊 Execution Summary:")
    summary = execution_results["execution_summary"]
    print(f"   - Tools executed: {summary['total_tools_executed']}")
    print(f"   - Successful tools: {summary['successful_tools']}")
    print(f"   - Total items: {summary['total_items_found']}")
    print(f"   - Sources: {summary['sources_used']}")
    print()
    
    # Examine each tool's contribution
    tool_results = execution_results.get("tool_results", {})
    
    for tool_name, result in tool_results.items():
        print(f"🔧 {tool_name.upper()}:")
        print(f"   Success: {result.get('success', 'not set')}")
        print(f"   Items: {len(result.get('items', []))}")
        
        items = result.get('items', [])
        if items:
            print(f"   Sample item structure:")
            first_item = items[0]
            for key, value in first_item.items():
                if isinstance(value, str) and len(value) > 80:
                    print(f"     - {key}: {value[:80]}...")
                else:
                    print(f"     - {key}: {value}")
        else:
            print(f"   Error: {result.get('error', 'No items')}")
        print()
    
    # Show the data quality comparison
    print("📈 Data Quality Analysis:")
    print("-" * 30)
    
    for tool_name, result in tool_results.items():
        items = result.get('items', [])
        if items:
            sample = items[0]
            
            # Count available fields
            fields = ['title', 'address', 'phone', 'website', 'rating', 'description', 'price']
            available_fields = [f for f in fields if sample.get(f)]
            
            print(f"{tool_name}: {len(available_fields)}/{len(fields)} fields populated")
            print(f"   Available: {available_fields}")
        else:
            print(f"{tool_name}: No items to analyze")
    
    print("\n🎯 Why synthesis might prefer certain sources:")
    print("   - Google Places: Complete venue data (address, phone, rating, etc.)")
    print("   - Eventbrite: Event-focused but less venue detail") 
    print("   - Web Search: Raw web content, needs more processing")

if __name__ == "__main__":
    asyncio.run(debug_synthesis_input())