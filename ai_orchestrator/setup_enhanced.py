#!/usr/bin/env python3
"""
Setup script for enhanced AI Orchestrator features
Runs database migrations and initializes services
"""
import os
import sys
import asyncio
import logging
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_flyway_migrations():
    """Run database migrations using Flyway (if available)"""
    logger.info("🔄 Running database migrations...")
    
    # Check if flyway is available
    try:
        result = subprocess.run(['flyway', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning("⚠️ Flyway not available, skipping migrations")
            return False
    except FileNotFoundError:
        logger.warning("⚠️ Flyway not found, skipping migrations")
        return False
    
    # Run migrations
    flyway_dir = os.path.join(os.path.dirname(__file__), 'flyway')
    if os.path.exists(flyway_dir):
        try:
            cmd = [
                'flyway', 
                f'-locations=filesystem:{flyway_dir}',
                'migrate'
            ]
            
            # Add database URL if available in environment
            if os.getenv('DATABASE_URL'):
                cmd.extend(['-url', os.getenv('DATABASE_URL')])
            elif os.getenv('DB_HOST'):
                db_url = f"jdbc:postgresql://{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'ai_orchestrator')}"
                cmd.extend(['-url', db_url])
                cmd.extend(['-user', os.getenv('DB_USER', 'postgres')])
                cmd.extend(['-password', os.getenv('DB_PASSWORD', '')])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ Database migrations completed successfully")
                return True
            else:
                logger.error(f"❌ Migration failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error running migrations: {e}")
            return False
    else:
        logger.warning("⚠️ Flyway directory not found, skipping migrations")
        return False

def run_manual_sql_setup():
    """Run SQL setup manually if Flyway is not available"""
    logger.info("🔄 Setting up database manually...")
    
    try:
        from server.db_config import get_db_pool
        
        async def setup_database():
            pool = await get_db_pool()
            async with pool.connection() as conn:
                async with conn.cursor() as cursor:
                    # Check if pgvector is available
                    await cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    logger.info("✅ pgvector extension enabled")
                    
                    # Check if PostGIS is available (optional)
                    try:
                        await cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                        logger.info("✅ PostGIS extension enabled")
                    except:
                        logger.warning("⚠️ PostGIS extension not available")
                    
                    # Check if basic tables exist
                    await cursor.execute("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name IN ('event', 'location', 'event_category')
                    """)
                    
                    tables = await cursor.fetchall()
                    logger.info(f"✅ Found {len(tables)} core tables in database")
                    
                    return True
        
        return asyncio.run(setup_database())
        
    except Exception as e:
        logger.error(f"❌ Manual database setup failed: {e}")
        return False

async def test_services():
    """Test that all services can be initialized"""
    logger.info("🧪 Testing service initialization...")
    
    try:
        # Test database connection
        from server.db_config import get_db_pool
        pool = await get_db_pool()
        logger.info("✅ Database connection established")
        
        # Test vector store
        from server.tools.vector_store import get_vector_store
        vector_store = get_vector_store()
        logger.info("✅ Vector store initialized")
        
        # Test enhanced services
        from server.tools.enhanced_api import get_enhanced_api_handler
        api_handler = await get_enhanced_api_handler()
        logger.info("✅ Enhanced API handler initialized")
        
        # Test system health
        health = await api_handler.get_system_health()
        logger.info("✅ System health check completed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Service initialization test failed: {e}")
        return False

def check_environment():
    """Check environment variables and configuration"""
    logger.info("🔍 Checking environment configuration...")
    
    # Required environment variables
    required_vars = [
        'DATABASE_URL',  # Or DB_HOST, DB_NAME, etc.
    ]
    
    # Optional but recommended
    optional_vars = [
        'SERPAPI_API_KEY',
        'BING_SEARCH_API_KEY',
        'GOOGLE_PLACES_API_KEY',
        'SCRAPINGBEE_API_KEY',
        'OPENAI_API_KEY'
    ]
    
    missing_required = []
    missing_optional = []
    
    # Check database configuration
    if not os.getenv('DATABASE_URL') and not os.getenv('DB_HOST'):
        missing_required.append('DATABASE_URL or DB_HOST')
    else:
        logger.info("✅ Database configuration found")
    
    # Check optional APIs
    for var in optional_vars:
        if os.getenv(var):
            logger.info(f"✅ {var} configured")
        else:
            missing_optional.append(var)
    
    if missing_required:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_required)}")
        return False
    
    if missing_optional:
        logger.warning(f"⚠️ Missing optional environment variables: {', '.join(missing_optional)}")
        logger.warning("   Some features may not work without these API keys")
    
    return True

async def main():
    """Main setup function"""
    logger.info("🚀 Setting up Enhanced AI Orchestrator")
    logger.info("=" * 50)
    
    # Step 1: Check environment
    if not check_environment():
        logger.error("❌ Environment check failed")
        return False
    
    # Step 2: Run database migrations
    migration_success = run_flyway_migrations()
    if not migration_success:
        logger.info("🔄 Trying manual database setup...")
        if not run_manual_sql_setup():
            logger.error("❌ Database setup failed")
            return False
    
    # Step 3: Test services
    if not await test_services():
        logger.error("❌ Service initialization failed")
        return False
    
    # Step 4: Summary
    logger.info("\n" + "=" * 50)
    logger.info("🎉 Enhanced AI Orchestrator setup completed!")
    logger.info("\n📋 Available make commands:")
    logger.info("   make scrape-enhanced      # Run enhanced web scraper")
    logger.info("   make test-enhanced        # Test enhanced features")
    logger.info("   make start-server         # Start the AI Orchestrator server")
    logger.info("\n🔗 Features enabled:")
    logger.info("   ✅ Event expiry & automatic cleanup")
    logger.info("   ✅ Enhanced geospatial search")
    logger.info("   ✅ Improved web search results")
    logger.info("\n💡 Next steps:")
    logger.info("   1. Run 'make test-enhanced' to test all features")
    logger.info("   2. Run 'make scrape-enhanced' to populate with date ideas")
    logger.info("   3. Run 'make start-server' to start the service")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)