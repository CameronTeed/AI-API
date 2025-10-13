#!/usr/bin/env python3
"""
Debug script to test parallel execution specifically
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

async def test_parallel_execution():
    """Test the exact parallel execution that's failing"""
    print("🚀 Testing Parallel Execution")
    print("=" * 40)
    
    # Initialize tools manager
    tools_manager = AgentToolsManager()
    
    query = "Find me cooking classes in ottawa"
    city = "Ottawa"
    
    print(f"📝 Query: {query}")
    print(f"🏙️ City: {city}")
    print()
    
    # Test the exact execution plan logic
    intent_analysis = tools_manager.analyze_query_intent(query, None)
    plan = await tools_manager.create_execution_plan(query, None)  # Pass query, not intent_analysis
    
    print(f"🧠 Intent: {intent_analysis['primary_intent']}")
    print(f"📋 Plan strategy: {plan['strategy']}")
    print(f"🔧 Parallel tools: {plan['parallel_execution']}")
    print()
    
    # Replicate the exact parallel execution logic
    base_args = {"query": query, "city": city}
    tasks = []
    
    for tool_name in plan["parallel_execution"]:
        print(f"⚙️ Preparing {tool_name}...")
        
        # Get filtered arguments for each specific tool
        tool_args = tools_manager._get_filtered_tool_args(tool_name, query, city, None)
        print(f"   Args: {tool_args}")
        
        # Add fallback execution
        fallbacks = plan["fallback_chains"].get(tool_name, [])
        tasks.append(tools_manager.execute_with_fallbacks(tool_name, fallbacks, **tool_args))
    
    print("\n🚀 Executing all tools in parallel...")
    
    # Execute all tools in parallel (exactly like the main code)
    parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results (exactly like the main code)
    print("\n📊 Processing results...")
    for i, result in enumerate(parallel_results):
        tool_name = plan["parallel_execution"][i]
        print(f"\n🔧 {tool_name}:")
        
        if isinstance(result, Exception):
            print(f"   ❌ Exception: {result}")
        else:
            print(f"   ✅ Success: {result.get('success', 'not set')}")
            print(f"   📊 Items: {len(result.get('items', []))}")
            print(f"   ⚠️ Error: {result.get('error', 'none')}")
            
            # Check the exact condition used in execute_with_fallbacks
            success = result.get("success", True)
            items = result.get("items", [])
            would_pass = success and items
            print(f"   🎯 Would pass condition: {would_pass} (success={success} and items={bool(items)})")

if __name__ == "__main__":
    asyncio.run(test_parallel_execution())