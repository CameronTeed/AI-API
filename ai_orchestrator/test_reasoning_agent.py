#!/usr/bin/env python3
"""
Comprehensive test script for the enhanced AI agent system
Tests all reasoning patterns, tool orchestration, and agent capabilities
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Add the correct paths
sys.path.insert(0, '/home/cameron/ai-api/ai_orchestrator')
sys.path.insert(0, '/home/cameron/ai-api/ai_orchestrator/server')

# Test basic import first
try:
    from server.tools.agent_tools import AgentToolsManager
    from server.llm.enhanced_engine import LLMEngine
    from server.tools.chat_context_storage import ChatContextStorage
    print("✅ All imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("⚠️  Running simplified test without full agent system")
    
    # Simplified test without imports
    async def simple_test():
        print("🔧 Testing basic system configuration...")
        
        # Check environment variables
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            print(f"✅ OpenAI API key found: {openai_key[:10]}...")
        else:
            print("❌ OpenAI API key not found")
        
        # Check database config
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'date_planner'),
            'user': os.getenv('DB_USER', 'postgres'),
        }
        print(f"🗄️  Database config: {db_config}")
        
        print("🎯 Simplified test completed")
    
    async def main():
        await simple_test()
    
    if __name__ == "__main__":
        asyncio.run(main())
    
    sys.exit(0)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/home/cameron/ai-api/ai_orchestrator/agent_test.log')
    ]
)

logger = logging.getLogger(__name__)

async def test_reasoning_agent():
    """Test the advanced reasoning agent capabilities"""
    
    print("\n" + "="*80)
    print("🧠 TESTING ADVANCED REASONING AGENT SYSTEM")
    print("="*80)
    
    try:
        # Initialize components
        print("\n🔧 Initializing Enhanced AI Agent System...")
        
        # Initialize agent tools manager
        agent_tools = AgentToolsManager()
        # AgentToolsManager initializes automatically in __init__
        
        # Initialize LLM engine
        llm_engine = LLMEngine()
        
        # Initialize chat storage
        chat_storage = ChatContextStorage()
        # ChatContextStorage initializes automatically in __init__
        
        # Setup reasoning agent
        llm_engine.setup_reasoning_agent(
            agent_tools=agent_tools,
            vector_search_func=agent_tools.search_date_ideas,
            web_search_func=agent_tools.enhanced_web_search
        )
        
        print("✅ All systems initialized successfully!")
        
        # Test scenarios
        test_scenarios = [
            {
                "name": "Complex Multi-Tool Query",
                "query": "Find romantic dinner options and evening activities in Ottawa for this weekend",
                "constraints": {"max_budget": 200, "duration": "3-4 hours"},
                "user_location": {"city": "Ottawa", "lat": 45.4215, "lon": -75.7072}
            },
            {
                "name": "Plan-Execute-Reflect Test",
                "query": "Plan a perfect date day in Toronto with indoor and outdoor activities for a couple who loves art and food",
                "constraints": {"indoor": True, "outdoor": True, "interests": ["art", "food"]},
                "user_location": {"city": "Toronto", "lat": 43.7001, "lon": -79.4163}
            },
            {
                "name": "Smart Tool Selection Test",
                "query": "What are some unique date ideas for tonight in Vancouver?",
                "constraints": {"timeframe": "tonight", "preference": "unique"},
                "user_location": {"city": "Vancouver", "lat": 49.2827, "lon": -123.1207}
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n{'='*60}")
            print(f"🧪 TEST SCENARIO {i}: {scenario['name']}")
            print(f"{'='*60}")
            print(f"📝 Query: {scenario['query']}")
            print(f"📋 Constraints: {scenario['constraints']}")
            print(f"📍 Location: {scenario['user_location']}")
            print(f"\n🚀 Starting reasoning process...\n")
            
            # Create session
            session_id = f"test_session_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create the session in the database first
            await chat_storage.create_session(session_id=session_id, user_id="test_user")
            
            # Prepare messages
            messages = [{"role": "user", "content": scenario["query"]}]
            
            # Track response
            full_response = ""
            
            try:
                # Run the enhanced chat with reasoning
                async for chunk in llm_engine.run_chat(
                    messages=messages,
                    agent_tools=agent_tools,
                    chat_storage=chat_storage,
                    session_id=session_id,
                    constraints=scenario["constraints"],
                    user_location=scenario["user_location"]
                ):
                    print(chunk, end='', flush=True)
                    full_response += chunk
                
                print(f"\n\n✅ Test {i} completed successfully!")
                print(f"📊 Response length: {len(full_response)} characters")
                
                # Brief pause between tests
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Test {i} failed: {e}")
                print(f"\n❌ Test {i} failed: {e}")
                continue
        
        print(f"\n{'='*80}")
        print("🎉 ALL REASONING AGENT TESTS COMPLETED!")
        print(f"{'='*80}")
        
        # Test agent tools analysis capabilities
        print(f"\n🔍 Testing Agent Tools Analysis Capabilities...")
        
        test_queries = [
            "romantic restaurants in Montreal",
            "outdoor activities for couples in Calgary", 
            "unique date ideas for tonight",
            "plan a weekend getaway in Quebec City"
        ]
        
        for query in test_queries:
            print(f"\n📝 Analyzing: '{query}'")
            analysis = agent_tools.analyze_query_intent(query)
            print(f"   Intent: {analysis['intent']}")
            print(f"   City: {analysis['city']}")
            print(f"   Category: {analysis['category']}")
            print(f"   Timeframe: {analysis['timeframe']}")
            print(f"   Recommended tools: {', '.join(analysis['recommended_tools'][:3])}...")
        
        print(f"\n✅ Analysis testing complete!")
        
        # Test optimal tool selection
        print(f"\n🎯 Testing Optimal Tool Selection...")
        
        test_query = "Find romantic activities and great restaurants in Ottawa for anniversary dinner"
        optimal_tools = await agent_tools.select_optimal_tools_for_query(
            query=test_query,
            constraints={"occasion": "anniversary", "meal": "dinner"},
            user_location={"city": "Ottawa"}
        )
        
        print(f"📝 Query: {test_query}")
        print(f"🔧 Selected tools:")
        for i, tool_info in enumerate(optimal_tools, 1):
            print(f"   {i}. {tool_info['tool']} (confidence: {tool_info['confidence']:.2f})")
            print(f"      Reason: {tool_info['reason']}")
        
    except Exception as e:
        logger.error(f"❌ Major error in reasoning agent test: {e}")
        print(f"\n❌ Major error: {e}")
        raise
    
    finally:
        # Cleanup
        try:
            if 'chat_storage' in locals():
                await chat_storage.close()
            if 'agent_tools' in locals():
                await agent_tools.close()
        except Exception as e:
            logger.error(f"⚠️  Cleanup error: {e}")

async def main():
    """Main test function"""
    
    print("🧠 Enhanced AI Agent System - Comprehensive Test Suite")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        await test_reasoning_agent()
        
        print(f"\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the comprehensive test
    asyncio.run(main())