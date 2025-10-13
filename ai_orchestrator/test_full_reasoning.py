#!/usr/bin/env python3
"""
Test the full reasoning agent with 'Find me sledding hills in ottawa'
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add project root to path
sys.path.append('/home/cameron/ai-api/ai_orchestrator')

from server.llm.reasoning_agent import ReasoningAgent
from server.tools.agent_tools import AgentToolsManager
import logging

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_full_reasoning_system():
    """Test the full reasoning system with sledding query"""
    
    print("🧠 TESTING FULL REASONING SYSTEM")
    print("=" * 60)
    print("Query: 'Find me sledding hills in ottawa'")
    print("Expected: Should use 5 tools for comprehensive search")
    print("=" * 60)
    
    # Create agent tools manager
    tools_manager = AgentToolsManager()
    
    # Create reasoning agent
    reasoning_agent = ReasoningAgent(tools_manager=tools_manager)
    
    # Test the query that should trigger 5-tool usage
    query = "Find me sledding hills in ottawa"
    
    try:
        # Run the reasoning process
        result = await reasoning_agent.process_query(query)
        
        print(f"\n🎯 REASONING RESULT:")
        print(f"Success: {result.get('success')}")
        print(f"Final Response Length: {len(result.get('response', ''))}")
        
        # Check execution details
        execution_details = result.get('execution_details', {})
        tool_calls = execution_details.get('tool_calls', [])
        
        print(f"\n🔧 TOOL EXECUTION:")
        print(f"Total tool calls made: {len(tool_calls)}")
        
        tool_names = set()
        for call in tool_calls:
            tool_name = call.get('tool', 'unknown')
            tool_names.add(tool_name)
            success = call.get('success', False)
            print(f"  • {tool_name}: {'✅' if success else '❌'}")
        
        print(f"\nUnique tools used: {len(tool_names)}")
        print(f"Tools: {list(tool_names)}")
        
        # Show if we got the expected 5 tools
        expected_tools = {
            'enhanced_web_search', 
            'google_places_search', 
            'search_date_ideas',
            'search_featured_dates',
            'eventbrite_search'
        }
        
        tools_used = set(tool_names)
        missing_tools = expected_tools - tools_used
        
        if len(tools_used) >= 4:  # Allow some flexibility
            print(f"✅ GOOD: Used {len(tools_used)} tools for comprehensive search")
        else:
            print(f"⚠️ LIMITED: Only used {len(tools_used)} tools")
            
        if missing_tools:
            print(f"Missing expected tools: {missing_tools}")
        
        # Check if we got sledding-specific results
        response = result.get('response', '')
        sledding_keywords = ['sledding', 'toboggan', 'hill', 'Ottawa', 'Open Ottawa']
        found_keywords = [kw for kw in sledding_keywords if kw.lower() in response.lower()]
        
        print(f"\n🎿 CONTENT ANALYSIS:")
        print(f"Sledding-related keywords found: {found_keywords}")
        print(f"Response mentions government data: {'open.ottawa.ca' in response.lower()}")
        print(f"Response mentions local blogs: {'ottawaisnotboring' in response.lower()}")
        
        if len(found_keywords) >= 3:
            print("✅ Response appears relevant to sledding hills")
        else:
            print("⚠️ Response may not be sledding-specific")
            
        # Show a snippet of the response
        print(f"\n📝 RESPONSE PREVIEW:")
        print(response[:300] + "..." if len(response) > 300 else response)
        
    except Exception as e:
        print(f"❌ ERROR in reasoning system: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_full_reasoning_system())