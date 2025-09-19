#!/usr/bin/env python3
"""
Example client for the AI Orchestrator service
"""

import asyncio
import grpc
from grpc import aio
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(__file__))

import chat_service_pb2
import chat_service_pb2_grpc

async def example_chat():
    """Example chat interaction with the AI Orchestrator"""
    
    # Create async channel
    channel = aio.insecure_channel('localhost:7000')
    
    # Set up auth metadata (disabled for now)
    # metadata = [('authorization', 'Bearer test_bearer_token')]
    metadata = []
    
    # Create stub
    stub = chat_service_pb2_grpc.AiOrchestratorStub(channel)
    
    try:
        # Create chat request with session ID
        session_id = f"example_session_{int(asyncio.get_event_loop().time())}"
        request = chat_service_pb2.ChatRequest(
            session_id=session_id,
            messages=[
                chat_service_pb2.ChatMessage(
                    role="user",
                    content="I want romantic date ideas in Ottawa under $100"
                )
            ],
            constraints=chat_service_pb2.Constraints(
                city="Ottawa",
                budgetTier=2,
                hours=180,
                categories=["Romantic"]
            ),
            stream=True
        )
        
        print(f"Sending chat request with session ID: {session_id}")
        print("User: I want romantic date ideas in Ottawa under $100")
        print("\nAI Response:")
        
        # Stream the response
        response_stream = stub.Chat(iter([request]), metadata=metadata)
        
        async for response in response_stream:
            # Print session ID from response
            if hasattr(response, 'session_id') and response.session_id:
                if not hasattr(example_chat, '_session_printed'):
                    print(f"Response from session: {response.session_id}")
                    example_chat._session_printed = True
            
            if response.text_delta:
                print(response.text_delta, end='', flush=True)
            
            if response.structured:
                print(f"\n\nStructured Answer:")
                print(f"Summary: {response.structured.summary}")
                for i, option in enumerate(response.structured.options):
                    print(f"\nOption {i+1}: {option.title}")
                    print(f"  Categories: {', '.join(option.categories)}")
                    print(f"  Price: {option.price}")
                    print(f"  Duration: {option.duration_min} minutes")
                    print(f"  Why it fits: {option.why_it_fits}")
                    print(f"  Website: {option.website}")
                    print(f"  Source: {option.source}")
            
            if response.done:
                print(f"\n\n✓ Chat completed")
                break
                
    except grpc.RpcError as e:
        print(f"gRPC error: {e.code()} - {e.details()}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await channel.close()

def main():
    """Main entry point"""
    print("AI Orchestrator Client Example")
    print("=" * 40)
    print("Note: Make sure the AI Orchestrator server is running on localhost:7000")
    print()
    
    try:
        asyncio.run(example_chat())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
