#!/usr/bin/env python3
"""
Quick test for cooking classes query to debug tool execution
"""

import asyncio
import sys
import os

sys.path.insert(0, '/home/cameron/ai-api/ai_orchestrator')
sys.path.insert(0, '/home/cameron/ai-api/ai_orchestrator/server')

from server.tools.agent_tools import AgentToolsManager
from server.llm.enhanced_engine import LLMEngine
from server.tools.chat_context_storage import ChatContextStorage

async def test_cooking_classes():
    """Test cooking classes query specifically"""
    
    print("🧪 Testing Cooking Classes Query")
    print("="*50)
    
    # Initialize components
    agent_tools = AgentToolsManager()
    llm_engine = LLMEngine()
    chat_storage = ChatContextStorage()
    
    # Setup reasoning agent
    llm_engine.setup_reasoning_agent(
        agent_tools=agent_tools,
        vector_search_func=agent_tools.search_date_ideas,
        web_search_func=agent_tools.enhanced_web_search
    )
    
    # Test the execution plan
    query = "Find me cooking classes in ottawa"
    
    print(f"📝 Query: {query}")
    print()
    
    # Test intent analysis
    analysis = agent_tools.analyze_query_intent(query)
    print(f"🧠 Intent Analysis:")
    print(f"   Intent: {analysis['intent']}")
    print(f"   Category: {analysis['category']}")
    print(f"   Recommended tools: {analysis['recommended_tools']}")
    print()
    
    # Test execution plan
    plan = await agent_tools.create_execution_plan(query)
    print(f"📋 Execution Plan:")
    print(f"   Strategy: {plan['strategy']}")
    print(f"   Primary tools: {plan['primary_tools']}")
    print(f"   Parallel execution: {plan['parallel_execution']}")
    print(f"   Sequential execution: {plan['sequential_execution']}")
    print()
    
    # Test actual execution
    print("🚀 Executing plan...")
    session_id = "test_cooking_classes"
    await chat_storage.create_session(session_id=session_id, user_id="test_user")
    
    messages = [{"role": "user", "content": query}]
    constraints = {}
    user_location = {"city": "Ottawa", "lat": 45.4215, "lon": -75.7072}
    
    print("💬 Response:")
    full_response = ""
    async for chunk in llm_engine.run_chat(
        messages=messages,
        agent_tools=agent_tools,
        chat_storage=chat_storage,
        session_id=session_id,
        constraints=constraints,
        user_location=user_location
    ):
        print(chunk, end='', flush=True)
        full_response += chunk
    
    print(f"\n\n📊 Response length: {len(full_response)} characters")
    
    # Cleanup
    await chat_storage.close()
    await agent_tools.close()

if __name__ == "__main__":
    asyncio.run(test_cooking_classes())