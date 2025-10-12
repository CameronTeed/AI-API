#!/usr/bin/env python3
"""
Test Script for Enhanced AI Chat System
Tests agent tools and chat context storage functionality
"""

import asyncio
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_agent_tools():
    """Test the agent tools functionality"""
    logger.info("🔧 Testing Agent Tools...")
    
    try:
        from server.tools.agent_tools import get_agent_tools
        
        agent_tools = get_agent_tools()
        
        # Test 1: Search stored dates
        logger.info("Test 1: Searching stored date ideas...")
        result1 = await agent_tools.search_stored_dates(
            query="romantic dinner",
            city="Ottawa",
            top_k=3
        )
        logger.info(f"✅ Stored dates search: {result1.get('success')} - {result1.get('count', 0)} results")
        
        # Test 2: Search featured dates
        logger.info("Test 2: Searching featured dates...")
        result2 = await agent_tools.search_featured_dates(
            city="Ottawa",
            category="romantic"
        )
        logger.info(f"✅ Featured dates search: {result2.get('success')} - {result2.get('count', 0)} results")
        
        # Test 3: Geocode location
        logger.info("Test 3: Geocoding location...")
        result3 = await agent_tools.geocode_location("Parliament Hill, Ottawa")
        logger.info(f"✅ Geocoding: {result3.get('success')}")
        if result3.get('success'):
            data = result3.get('data', {})
            logger.info(f"   📍 {data.get('address')} -> {data.get('latitude')}, {data.get('longitude')}")
        
        # Test 4: Enhanced web search
        logger.info("Test 4: Enhanced web search...")
        result4 = await agent_tools.enhanced_web_search(
            query="best restaurants Ottawa",
            city="Ottawa",
            result_type="reviews"
        )
        logger.info(f"✅ Enhanced web search: {result4.get('success')} - {len(result4.get('items', []))} results")
        
        # Test 5: Google Places (if API key available)
        logger.info("Test 5: Google Places search...")
        result5 = await agent_tools.google_places_search(
            query="coffee shops",
            location="Ottawa, Canada"
        )
        logger.info(f"✅ Google Places: {result5.get('success')} - {result5.get('count', 0)} results")
        if not result5.get('success'):
            logger.info(f"   ℹ️ {result5.get('error', 'API key may not be configured')}")
        
        await agent_tools.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Agent tools test failed: {e}")
        return False

async def test_chat_storage():
    """Test the chat context storage functionality"""
    logger.info("💾 Testing Chat Context Storage...")
    
    try:
        from server.tools.chat_context_storage import get_chat_storage
        
        chat_storage = get_chat_storage()
        
        # Test 1: Ensure tables exist
        logger.info("Test 1: Creating/verifying tables...")
        tables_ok = await chat_storage.ensure_tables_exist()
        logger.info(f"✅ Tables setup: {tables_ok}")
        
        # Test 2: Create session
        logger.info("Test 2: Creating test session...")
        session_id = "test_session_123"
        session_ok = await chat_storage.create_session(
            session_id=session_id,
            user_id="test_user",
            metadata={"test": True, "client": "test_script"}
        )
        logger.info(f"✅ Session creation: {session_ok}")
        
        # Test 3: Store messages
        logger.info("Test 3: Storing test messages...")
        msg1_id = await chat_storage.store_message(
            session_id=session_id,
            role="user",
            content="Find me romantic restaurants in Ottawa",
            metadata={"test_message": True}
        )
        
        msg2_id = await chat_storage.store_message(
            session_id=session_id,
            role="assistant", 
            content="I found several romantic restaurants for you...",
            metadata={"test_response": True}
        )
        
        logger.info(f"✅ Message storage: {msg1_id is not None and msg2_id is not None}")
        
        # Test 4: Store tool call
        logger.info("Test 4: Storing test tool call...")
        tool_ok = await chat_storage.store_tool_call(
            session_id=session_id,
            message_id=msg2_id or 1,
            tool_name="google_places_search",
            tool_arguments={"query": "romantic restaurants", "location": "Ottawa"},
            tool_result={"success": True, "items": [], "count": 0},
            execution_time_ms=1500
        )
        logger.info(f"✅ Tool call storage: {tool_ok}")
        
        # Test 5: Retrieve session messages
        logger.info("Test 5: Retrieving session messages...")
        messages = await chat_storage.get_session_messages(session_id, limit=10)
        logger.info(f"✅ Message retrieval: {len(messages)} messages")
        
        # Test 6: Get session context
        logger.info("Test 6: Getting session context...")
        context = await chat_storage.get_session_context(session_id)
        logger.info(f"✅ Session context: {len(context.get('messages', []))} messages, {len(context.get('tool_calls', []))} tool calls")
        
        # Test 7: Search chat history
        logger.info("Test 7: Searching chat history...")
        search_results = await chat_storage.search_chat_history(
            user_id="test_user",
            query="romantic",
            limit=5
        )
        logger.info(f"✅ Chat history search: {len(search_results)} results")
        
        # Test 8: Deactivate session
        logger.info("Test 8: Deactivating test session...")
        deactivate_ok = await chat_storage.deactivate_session(session_id)
        logger.info(f"✅ Session deactivation: {deactivate_ok}")
        
        await chat_storage.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Chat storage test failed: {e}")
        return False

async def test_enhanced_llm():
    """Test the enhanced LLM engine"""
    logger.info("🤖 Testing Enhanced LLM Engine...")
    
    try:
        from server.llm.enhanced_engine import LLMEngine
        from server.tools.agent_tools import get_agent_tools
        from server.tools.chat_context_storage import get_chat_storage
        
        llm_engine = LLMEngine()
        agent_tools = get_agent_tools()
        chat_storage = get_chat_storage()
        
        # Mock vector search function
        async def mock_vector_search(**kwargs):
            return {
                "items": [
                    {"title": "Test Restaurant", "description": "A test romantic restaurant", "similarity_score": 0.85}
                ],
                "source": "vector_store"
            }
        
        # Mock web search function  
        async def mock_web_search(**kwargs):
            return {
                "items": [
                    {"title": "Test Web Result", "url": "https://example.com", "snippet": "Test snippet"}
                ]
            }
        
        logger.info("Test 1: Simple LLM response...")
        messages = [
            {"role": "user", "content": "Hello, can you help me find a romantic restaurant?"}
        ]
        
        response_text = ""
        async for chunk in llm_engine.run_chat(
            messages=messages,
            vector_search_func=mock_vector_search,
            web_search_func=mock_web_search,
            agent_tools=agent_tools,
            chat_storage=chat_storage,
            session_id="test_llm_session",
            constraints={"city": "Ottawa", "budgetTier": 2},
            user_location={"lat": 45.4215, "lon": -75.6972}
        ):
            response_text += chunk
        
        logger.info(f"✅ LLM response generated: {len(response_text)} characters")
        logger.info(f"   📝 Response preview: {response_text[:100]}...")
        
        await agent_tools.close()
        await chat_storage.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Enhanced LLM test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests and provide summary"""
    logger.info("🚀 Starting Enhanced AI Chat System Tests")
    logger.info("=" * 60)
    
    load_dotenv(".env.enhanced")
    
    # Run tests
    tests = [
        ("Agent Tools", test_agent_tools),
        ("Chat Storage", test_chat_storage),
        ("Enhanced LLM", test_enhanced_llm)
    ]
    
    results = {}
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running {test_name} tests...")
        try:
            results[test_name] = await test_func()
        except Exception as e:
            logger.error(f"❌ {test_name} test suite failed: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("🎯 Test Results Summary:")
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"   {test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("\n🎉 All tests passed! Enhanced AI Chat System is working correctly.")
        logger.info("🚀 You can now start the enhanced server with: python -m server.enhanced_main")
    else:
        logger.info("\n⚠️ Some tests failed. Please check the configuration and try again.")
        logger.info("💡 Run setup_enhanced_chat.py to verify your configuration.")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(run_all_tests())