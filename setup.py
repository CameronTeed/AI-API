#!/usr/bin/env python3
"""
Setup script for AI Date Ideas Orchestrator
Initializes database, vector store, and verifies configuration
"""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
from server.db_config import get_db_config, test_connection
from server.tools.vector_search import PostgreSQLVectorStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_environment() -> bool:
    """Check if all required environment variables are set"""
    logger.info("🔍 Checking environment variables...")
    
    load_dotenv()
    
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API key for LLM',
        'DB_HOST': 'Database host',
        'DB_PORT': 'Database port',
        'DB_USER': 'Database user',
        'DB_PASSWORD': 'Database password',
        'DB_NAME': 'Database name',
    }
    
    optional_vars = {
        'GOOGLE_PLACES_API_KEY': 'Google Places API (for venue search)',
        'GOOGLE_MAPS_API_KEY': 'Google Maps API (for directions)',
        'SEARCH_API_KEY': 'Search API key (for web search)',
    }
    
    missing_required = []
    for var, desc in required_vars.items():
        if not os.getenv(var):
            missing_required.append(f"{var} ({desc})")
            logger.error(f"  ❌ Missing: {var}")
        else:
            logger.info(f"  ✅ {var}")
    
    for var, desc in optional_vars.items():
        if not os.getenv(var):
            logger.warning(f"  ⚠️  Optional not set: {var} ({desc})")
        else:
            logger.info(f"  ✅ {var}")
    
    if missing_required:
        logger.error("\n❌ Missing required environment variables:")
        for var in missing_required:
            logger.error(f"   - {var}")
        logger.error("\nPlease set these in your .env file")
        return False
    
    logger.info("✅ Environment check passed")
    return True


def check_database_connection() -> bool:
    """Test database connection"""
    logger.info("🔍 Testing database connection...")
    
    try:
        if test_connection():
            logger.info("✅ Database connection successful")
            return True
        else:
            logger.error("❌ Database connection failed")
            return False
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        return False


async def initialize_vector_store() -> bool:
    """Initialize vector store with sample data if empty"""
    logger.info("🔍 Checking vector store...")
    
    try:
        vector_store = PostgreSQLVectorStore()
        
        # Check if vector store has data
        stats = await vector_store.get_stats()
        total_ideas = stats.get('total_date_ideas', 0)
        
        if total_ideas > 0:
            logger.info(f"✅ Vector store already initialized with {total_ideas} date ideas")
            return True
        
        logger.info("📚 Vector store is empty, loading sample data...")
        
        # Load sample data
        sample_data_path = Path(__file__).parent / "data" / "sample_date_ideas.json"
        
        if not sample_data_path.exists():
            logger.warning("⚠️  No sample data found. Vector store is empty.")
            logger.warning("   Use the web UI to add date ideas manually.")
            return True
        
        with open(sample_data_path, 'r') as f:
            sample_data = json.load(f)
        
        logger.info(f"📊 Loading {len(sample_data)} sample date ideas...")
        
        # Add sample data to vector store
        for idea in sample_data:
            await vector_store.add_date_idea(
                name=idea.get('name', ''),
                description=idea.get('description', ''),
                city=idea.get('city', ''),
                price_tier=idea.get('price_tier', 2),
                duration_minutes=idea.get('duration_minutes'),
                indoor=idea.get('indoor', False),
                categories=idea.get('categories', []),
                unique_features=idea.get('unique_features', []),
                is_featured=idea.get('is_featured', False)
            )
        
        logger.info("✅ Sample data loaded successfully")
        
        # Show stats
        stats = await vector_store.get_stats()
        logger.info(f"📊 Vector store stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Vector store initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_env_template():
    """Create .env template file if it doesn't exist"""
    env_path = Path(__file__).parent / '.env'
    env_example_path = Path(__file__).parent / '.env.example'
    
    if env_path.exists():
        return
    
    template = """# AI Date Ideas Orchestrator Configuration

# === REQUIRED: OpenAI API ===
OPENAI_API_KEY=your_openai_api_key_here

# === REQUIRED: Database Configuration ===
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_db_password
DB_NAME=ai_orchestrator

# === OPTIONAL: Google Services (for real-time venue search) ===
GOOGLE_PLACES_API_KEY=your_google_places_api_key_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# === OPTIONAL: Web Search ===
SEARCH_PROVIDER=serpapi
SEARCH_API_KEY=your_search_api_key_here

# === Application Settings ===
PORT=7000
DEFAULT_CITY=Ottawa
LOG_LEVEL=INFO
"""
    
    with open(env_example_path, 'w') as f:
        f.write(template)
    
    logger.info(f"📝 Created .env.example template")
    logger.info("   Copy to .env and fill in your values")


async def main():
    """Main setup function"""
    logger.info("🚀 AI Date Ideas Orchestrator Setup")
    logger.info("=" * 60)
    
    # Create env template if needed
    create_env_template()
    
    # Check environment
    if not check_environment():
        logger.error("\n❌ Setup failed: Environment variables not configured")
        logger.info("\n📝 Next steps:")
        logger.info("   1. Copy .env.example to .env")
        logger.info("   2. Fill in your API keys and database credentials")
        logger.info("   3. Run this setup script again")
        sys.exit(1)
    
    # Check database
    if not check_database_connection():
        logger.error("\n❌ Setup failed: Cannot connect to database")
        logger.info("\n📝 Next steps:")
        logger.info("   1. Ensure PostgreSQL is running")
        logger.info("   2. Verify database credentials in .env")
        logger.info("   3. Create database if it doesn't exist:")
        logger.info("      psql -U postgres -c 'CREATE DATABASE ai_orchestrator;'")
        logger.info("   4. Install pgvector extension:")
        logger.info("      psql -U postgres -d ai_orchestrator -c 'CREATE EXTENSION vector;'")
        sys.exit(1)
    
    # Initialize vector store
    if not await initialize_vector_store():
        logger.error("\n❌ Setup failed: Vector store initialization error")
        sys.exit(1)
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Setup completed successfully!")
    logger.info("\n📝 Next steps:")
    logger.info("   1. Start the chat server:")
    logger.info("      make start-server")
    logger.info("      (or: python3 -m server.main)")
    logger.info("")
    logger.info("   2. Start the admin web UI:")
    logger.info("      make web-ui")
    logger.info("      (or: python3 web_ui.py)")
    logger.info("")
    logger.info("🎉 Your AI Date Ideas system is ready!")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Setup failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
