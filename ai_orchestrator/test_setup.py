#!/usr/bin/env python3
"""
Simple test script to verify the AI orchestrator setup
"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all modules can be imported"""
    try:
        # Test protobuf imports
        import chat_service_pb2
        import chat_service_pb2_grpc
        import date_ideas_service_pb2
        import date_ideas_service_pb2_grpc
        print("✓ Protobuf imports successful")
        
        # Test server modules
        from server.main import main
        from server.chat_handler import ChatHandler
        from server.tools.db_client import DatabaseClient
        from server.tools.web_search import WebSearchClient
        from server.llm.engine import LLMEngine
        print("✓ Server module imports successful")
        
        # Test schemas
        from server.schemas import DateIdea, Option, StructuredAnswer
        print("✓ Schema imports successful")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_environment():
    """Test environment configuration"""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠ Missing environment variables: {missing_vars}")
        print("  (This is expected for testing)")
    else:
        print("✓ All required environment variables set")
    
    optional_vars = ['SEARCH_PROVIDER', 'JAVA_GRPC_TARGET', 'AI_BEARER_TOKEN']
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  {var}: {value}")
    
    return True

def main():
    """Run all tests"""
    print("Testing AI Orchestrator Setup")
    print("=" * 40)
    
    success = True
    
    print("\n1. Testing imports...")
    success &= test_imports()
    
    print("\n2. Testing environment...")
    success &= test_environment()
    
    if success:
        print(f"\n✓ All tests passed! Ready to start server:")
        print(f"  python3 -m ai_orchestrator.server.main")
    else:
        print(f"\n✗ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
