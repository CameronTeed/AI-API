#!/usr/bin/env python3
"""
Quick setup and test script for the AI Date Ideas Manager Web UI
"""
import os
import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_requirements():
    """Install required packages"""
    logger.info("📦 Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        logger.info("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install requirements: {e}")
        return False

def test_imports():
    """Test if all required modules can be imported"""
    logger.info("🔍 Testing imports...")
    
    required_modules = [
        'fastapi',
        'uvicorn', 
        'jinja2',
        'requests',
        'bs4',  # beautifulsoup4
        'feedparser',
        'sentence_transformers',
        'psycopg',
        'dotenv'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            logger.info(f"  ✅ {module}")
        except ImportError:
            logger.error(f"  ❌ {module}")
            missing_modules.append(module)
    
    if missing_modules:
        logger.error(f"Missing modules: {missing_modules}")
        return False
    
    logger.info("✅ All imports successful")
    return True

def check_database():
    """Check database connection"""
    logger.info("🔍 Testing database connection...")
    try:
        from server.db_config import test_connection
        if test_connection():
            logger.info("✅ Database connection successful")
            return True
        else:
            logger.warning("⚠️  Database connection failed")
            return False
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

def run_web_ui():
    """Run the web UI"""
    logger.info("🚀 Starting Web UI...")
    try:
        from web_ui import main
        main()
    except KeyboardInterrupt:
        logger.info("👋 Web UI stopped by user")
    except Exception as e:
        logger.error(f"❌ Web UI failed: {e}")

def main():
    """Main function"""
    print("🎯 AI Date Ideas Manager - Quick Setup & Test")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("web_ui.py"):
        logger.error("❌ web_ui.py not found. Please run from the ai_orchestrator directory.")
        sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        logger.error("❌ Failed to install requirements. Please install manually:")
        logger.error("pip install -r requirements.txt")
        sys.exit(1)
    
    # Test imports
    if not test_imports():
        logger.error("❌ Import test failed. Please check your installation.")
        sys.exit(1)
    
    # Test database
    db_ok = check_database()
    if not db_ok:
        logger.warning("⚠️  Database connection failed. Web UI will still work but with limited functionality.")
        logger.warning("To enable full functionality:")
        logger.warning("1. Start PostgreSQL")
        logger.warning("2. Run: python init_database.py")
        logger.warning("3. Set environment variables in .env file")
    
    print("\n🎉 Setup completed!")
    print("📋 Available features:")
    print("  • Add, edit, delete date ideas via web form")
    print("  • Semantic search with vector embeddings")
    print("  • Web scraping from Yelp, Eventbrite, TripAdvisor")
    print("  • Import/export JSON files")
    print("  • REST API endpoints")
    
    print("\n🌐 Web UI will start at: http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    
    input("\nPress Enter to start the Web UI...")
    
    # Run the web UI
    run_web_ui()

if __name__ == "__main__":
    main()