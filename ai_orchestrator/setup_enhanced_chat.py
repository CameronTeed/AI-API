#!/usr/bin/env python3
"""
Enhanced AI Orchestrator Setup Script
Sets up the enhanced chat system with agent tools and context storage
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def create_env_template():
    """Create an enhanced .env template file"""
    template = """# Enhanced AI Orchestrator Configuration

# === CORE SETTINGS ===
OPENAI_API_KEY=your_openai_api_key_here
PORT=7000
USE_ENHANCED_CHAT=true

# === DATABASE SETTINGS ===
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_db_password
DB_NAME=ai_orchestrator

# === GOOGLE SERVICES ===
GOOGLE_PLACES_API_KEY=your_google_places_api_key_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# === SEARCH PROVIDERS ===
SEARCH_PROVIDER=serpapi
SEARCH_API_KEY=your_search_api_key_here

# === DEFAULT SETTINGS ===
DEFAULT_CITY=Ottawa
AI_BEARER_TOKEN=your_bearer_token_here
JAVA_GRPC_TARGET=localhost:8081

# === OPTIONAL FEATURES ===
# Redis for caching (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# === LOGGING ===
LOG_LEVEL=DEBUG
LOG_FILE_PATH=/tmp/ai_orchestrator.log
"""
    
    env_path = ".env.enhanced"
    if not os.path.exists(env_path):
        with open(env_path, 'w') as f:
            f.write(template)
        print(f"✅ Created enhanced environment template: {env_path}")
        print("📝 Please edit this file with your API keys and settings")
    else:
        print(f"ℹ️ Enhanced environment template already exists: {env_path}")

def check_required_packages():
    """Check if required packages are installed"""
    required_packages = [
        'grpcio',
        'openai',
        'googlemaps',
        'geopy',
        'psycopg',
        'httpx',
        'beautifulsoup4',
        'sentence_transformers',
        'pgvector'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n🔧 Missing packages: {missing_packages}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("\n🎉 All required packages are installed!")
    return True

async def test_database_connection():
    """Test database connection and setup tables"""
    load_dotenv(".env.enhanced")
    
    try:
        from server.tools.chat_context_storage import get_chat_storage
        
        print("🔌 Testing database connection...")
        chat_storage = get_chat_storage()
        
        # Test connection and create tables
        success = await chat_storage.ensure_tables_exist()
        if success:
            print("✅ Database connection successful and tables created!")
            return True
        else:
            print("❌ Database table creation failed")
            return False
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("🔧 Please check your database settings in .env.enhanced")
        return False

async def test_google_services():
    """Test Google Services integration"""
    load_dotenv(".env.enhanced")
    
    google_api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not google_api_key or google_api_key == 'your_google_places_api_key_here':
        print("⚠️ Google Places API key not configured")
        return False
    
    try:
        from server.tools.agent_tools import get_agent_tools
        
        print("🗺️ Testing Google Places API...")
        agent_tools = get_agent_tools()
        
        # Test a simple search
        result = await agent_tools.google_places_search(
            query="coffee shops",
            location="Ottawa, Canada"
        )
        
        if result.get('success'):
            print(f"✅ Google Places API working! Found {result.get('count', 0)} results")
            return True
        else:
            print(f"❌ Google Places API test failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Google Services test failed: {e}")
        return False

def test_openai_connection():
    """Test OpenAI API connection"""
    load_dotenv(".env.enhanced")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print("❌ OpenAI API key not configured")
        return False
    
    try:
        from openai import OpenAI
        
        print("🤖 Testing OpenAI API connection...")
        client = OpenAI(api_key=api_key)
        
        # Simple test request
        response = client.models.list()
        if response:
            print("✅ OpenAI API connection successful!")
            return True
        else:
            print("❌ OpenAI API test failed")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI API test failed: {e}")
        return False

async def run_setup():
    """Run the complete setup process"""
    print("🚀 Enhanced AI Orchestrator Setup")
    print("=" * 50)
    
    # Step 1: Create environment template
    print("\n1. Creating environment configuration...")
    create_env_template()
    
    # Step 2: Check packages
    print("\n2. Checking required packages...")
    packages_ok = check_required_packages()
    if not packages_ok:
        print("❌ Please install missing packages before continuing")
        return False
    
    # Step 3: Test OpenAI
    print("\n3. Testing OpenAI API...")
    openai_ok = test_openai_connection()
    
    # Step 4: Test database
    print("\n4. Testing database connection...")
    db_ok = await test_database_connection()
    
    # Step 5: Test Google services
    print("\n5. Testing Google Services...")
    google_ok = await test_google_services()
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 Setup Summary:")
    print(f"   📦 Packages: {'✅' if packages_ok else '❌'}")
    print(f"   🤖 OpenAI API: {'✅' if openai_ok else '❌'}")
    print(f"   🗄️ Database: {'✅' if db_ok else '❌'}")
    print(f"   🗺️ Google Services: {'✅' if google_ok else '⚠️'}")
    
    if all([packages_ok, openai_ok, db_ok]):
        print("\n🎉 Enhanced AI Orchestrator is ready to use!")
        print("🚀 Start the server with: python -m server.enhanced_main")
        if not google_ok:
            print("ℹ️ Google Services optional - configure GOOGLE_PLACES_API_KEY for full features")
        return True
    else:
        print("\n❌ Setup incomplete. Please fix the issues above.")
        return False

def print_usage_examples():
    """Print usage examples for the enhanced system"""
    print("\n📚 Enhanced AI Orchestrator Usage Examples:")
    print("=" * 50)
    
    examples = [
        {
            "title": "🔍 Database Search",
            "description": "Search stored date ideas with semantic similarity",
            "query": "Find romantic restaurants with live music in Ottawa"
        },
        {
            "title": "🌟 Featured Dates",
            "description": "Find unique, high-quality date experiences",
            "query": "Show me featured unique date ideas in my city"
        },
        {
            "title": "🗺️ Google Places Integration",
            "description": "Real-time venue search with details",
            "query": "Find art galleries near downtown with current hours"
        },
        {
            "title": "🌐 Web Scraping",
            "description": "Get live venue information from websites",
            "query": "What events are happening at [venue website] this weekend?"
        },
        {
            "title": "📍 Location-Based Search",
            "description": "Find venues near specific coordinates",
            "query": "Find date spots within 5km of my location"
        },
        {
            "title": "🗺️ Directions and Travel",
            "description": "Get travel information between locations",
            "query": "How do I get from my hotel to the restaurant?"
        }
    ]
    
    for example in examples:
        print(f"\n{example['title']}")
        print(f"   {example['description']}")
        print(f"   💬 \"{example['query']}\"")

if __name__ == "__main__":
    async def main():
        success = await run_setup()
        if success:
            print_usage_examples()
    
    asyncio.run(main())