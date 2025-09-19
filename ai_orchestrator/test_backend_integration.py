#!/usr/bin/env python3
"""
Test client for the AI Orchestrator backend integration
Run this to test your backend integration
"""
import grpc
import chat_service_pb2
import chat_service_pb2_grpc
import sys
import time

def test_basic_connection():
    """Test basic gRPC connection"""
    print("🔗 Testing gRPC connection...")
    
    try:
        channel = grpc.insecure_channel('localhost:50051')
        stub = chat_service_pb2_grpc.AiOrchestratorStub(channel)
        
        # Test connection with a simple request
        messages = [
            chat_service_pb2.ChatMessage(
                role="user",
                content="Hello, are you working?"
            )
        ]
        
        request = chat_service_pb2.ChatRequest(
            messages=messages,
            stream=True
        )
        
        response_stream = stub.Chat(iter([request]))
        
        # Get first response to verify connection
        first_response = next(response_stream)
        print("✅ Connection successful!")
        channel.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Make sure the server is running: python3 -m server.main")
        return False

def test_date_idea_request():
    """Test a complete date idea request with entity references"""
    print("\n🎯 Testing date idea request...")
    
    try:
        channel = grpc.insecure_channel('localhost:50051')
        stub = chat_service_pb2_grpc.AiOrchestratorStub(channel)
        
        # Create a comprehensive request
        messages = [
            chat_service_pb2.ChatMessage(
                role="user",
                content="I want a romantic date idea in New York for around $50-75"
            )
        ]
        
        constraints = chat_service_pb2.Constraints(
            city="New York",
            budgetTier=2,  # $$
            categories=["romantic"]
        )
        
        user_location = chat_service_pb2.UserLocation(
            lat=40.7128,
            lon=-74.0060
        )
        
        request = chat_service_pb2.ChatRequest(
            messages=messages,
            constraints=constraints,
            userLocation=user_location,
            stream=True
        )
        
        # Process streaming response
        print("📡 Sending request...")
        response_stream = stub.Chat(iter([request]))
        
        full_text = ""
        structured_data = None
        
        print("💬 AI Response:")
        print("-" * 50)
        
        for response in response_stream:
            if response.text_delta:
                full_text += response.text_delta
                print(response.text_delta, end='', flush=True)
            
            if response.structured:
                structured_data = response.structured
            
            if response.done:
                break
        
        print("\n" + "-" * 50)
        
        # Test entity references
        if structured_data:
            print(f"\n📊 Structured Response:")
            print(f"Summary: {structured_data.summary}")
            print(f"Options: {len(structured_data.options)}")
            
            for i, option in enumerate(structured_data.options, 1):
                print(f"\n--- Option {i}: {option.title} ---")
                print(f"Categories: {', '.join(option.categories)}")
                print(f"Price: {option.price}")
                print(f"Duration: {option.duration_min} minutes")
                print(f"Source: {option.source}")
                
                # Test entity references
                if option.entity_references:
                    refs = option.entity_references
                    print(f"\n🔗 Entity References:")
                    print(f"Primary: {refs.primary_entity.title} ({refs.primary_entity.type})")
                    print(f"  URL: {refs.primary_entity.url}")
                    
                    if refs.related_entities:
                        print(f"Related ({len(refs.related_entities)}):")
                        for entity in refs.related_entities:
                            print(f"  - {entity.type}: {entity.title}")
                            print(f"    URL: {entity.url}")
                    else:
                        print("⚠️  No related entities found")
                else:
                    print("⚠️  No entity references found")
        else:
            print("⚠️  No structured data received")
        
        channel.close()
        print("\n✅ Date idea request test completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Date idea request failed: {e}")
        return False

def test_multiple_requests():
    """Test multiple different requests"""
    print("\n🔄 Testing multiple request types...")
    
    test_cases = [
        {
            "query": "outdoor adventure in Denver",
            "city": "Denver",
            "categories": ["outdoor", "adventure"]
        },
        {
            "query": "indoor activities for a rainy day",
            "indoor": True,
            "categories": ["indoor"]
        },
        {
            "query": "budget-friendly fun activities",
            "budget_tier": 1,
            "categories": ["fun"]
        }
    ]
    
    try:
        channel = grpc.insecure_channel('localhost:50051')
        stub = chat_service_pb2_grpc.AiOrchestratorStub(channel)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- Test {i}: {test_case['query']} ---")
            
            messages = [
                chat_service_pb2.ChatMessage(
                    role="user",
                    content=test_case['query']
                )
            ]
            
            constraints = chat_service_pb2.Constraints()
            if 'city' in test_case:
                constraints.city = test_case['city']
            if 'budget_tier' in test_case:
                constraints.budgetTier = test_case['budget_tier']
            if 'indoor' in test_case:
                constraints.indoor = test_case['indoor']
            if 'categories' in test_case:
                constraints.categories.extend(test_case['categories'])
            
            request = chat_service_pb2.ChatRequest(
                messages=messages,
                constraints=constraints,
                stream=True
            )
            
            response_stream = stub.Chat(iter([request]))
            
            # Count responses
            text_chunks = 0
            structured_received = False
            
            for response in response_stream:
                if response.text_delta:
                    text_chunks += 1
                if response.structured:
                    structured_received = True
                if response.done:
                    break
            
            print(f"✅ Received {text_chunks} text chunks, structured: {structured_received}")
        
        channel.close()
        print("\n✅ Multiple requests test completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Multiple requests test failed: {e}")
        return False

def main():
    """Run all backend integration tests"""
    print("🚀 AI Orchestrator Backend Integration Test")
    print("=" * 50)
    
    # Test 1: Basic connection
    if not test_basic_connection():
        print("\n❌ Basic connection failed. Stopping tests.")
        return False
    
    # Test 2: Date idea request
    if not test_date_idea_request():
        print("\n❌ Date idea request failed.")
        return False
    
    # Test 3: Multiple requests
    if not test_multiple_requests():
        print("\n❌ Multiple requests test failed.")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All backend integration tests passed!")
    print("\nYour backend is ready to use. Next steps:")
    print("1. Implement the API endpoints mentioned in BACKEND_INTEGRATION.md")
    print("2. Connect your frontend to the gRPC service")
    print("3. Use entity references to create clickable keywords")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
