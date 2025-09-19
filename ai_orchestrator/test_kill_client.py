#!/usr/bin/env python3
"""
Test client for the KillChat and HealthCheck endpoints
"""

import asyncio
import grpc
from grpc import aio
import chat_service_pb2
import chat_service_pb2_grpc


async def test_health_check():
    """Test the health check endpoint"""
    print("🩺 Testing Health Check endpoint...")
    
    try:
        async with aio.insecure_channel('localhost:7000') as channel:
            stub = chat_service_pb2_grpc.AiOrchestratorStub(channel)
            
            request = chat_service_pb2.HealthCheckRequest()
            response = await stub.HealthCheck(request)
            
            print(f"✅ Health Check Response:")
            print(f"   Status: {response.status}")
            print(f"   Message: {response.message}")
            print(f"   Timestamp: {response.timestamp}")
            print(f"   Details: {dict(response.details)}")
            
            return True
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


async def test_kill_chat():
    """Test the kill chat endpoint"""
    print("\n🔪 Testing Kill Chat endpoint...")
    
    try:
        async with aio.insecure_channel('localhost:7000') as channel:
            stub = chat_service_pb2_grpc.AiOrchestratorStub(channel)
            
            # Test killing a non-existent session
            request = chat_service_pb2.KillChatRequest(
                session_id="test_session_123",
                reason="Testing kill functionality"
            )
            response = await stub.KillChat(request)
            
            print(f"📋 Kill Chat Response (non-existent session):")
            print(f"   Success: {response.success}")
            print(f"   Message: {response.message}")
            
            # Test killing with no session ID
            request = chat_service_pb2.KillChatRequest(
                reason="Testing default session kill"
            )
            response = await stub.KillChat(request)
            
            print(f"\n📋 Kill Chat Response (default session):")
            print(f"   Success: {response.success}")
            print(f"   Message: {response.message}")
            
            return True
            
    except Exception as e:
        print(f"❌ Kill chat test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 Starting gRPC endpoint tests...\n")
    
    # Test health check
    health_ok = await test_health_check()
    
    # Test kill chat
    kill_ok = await test_kill_chat()
    
    print(f"\n📊 Test Results:")
    print(f"   Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"   Kill Chat: {'✅ PASS' if kill_ok else '❌ FAIL'}")
    
    if health_ok and kill_ok:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed. Make sure the server is running.")


if __name__ == "__main__":
    asyncio.run(main())