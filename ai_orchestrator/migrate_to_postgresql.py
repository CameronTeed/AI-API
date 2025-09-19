#!/usr/bin/env python3
"""
Migrate existing pickle-based vector store data to PostgreSQL
"""
import os
import sys
import pickle
import logging
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from server.tools.postgresql_vector_store import PostgreSQLVectorStore
from server.db_config import get_db_config, test_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_pickle_files():
    """Find existing pickle files in the data directory"""
    data_dir = Path(__file__).parent / "data"
    pickle_files = []
    
    if data_dir.exists():
        pickle_files = list(data_dir.glob("*.pkl"))
    
    # Also check the default location
    default_file = data_dir / "date_ideas_vector_store.pkl"
    if default_file.exists() and default_file not in pickle_files:
        pickle_files.append(default_file)
    
    return pickle_files

def load_pickle_data(pickle_file: Path):
    """Load data from a pickle file"""
    try:
        with open(pickle_file, 'rb') as f:
            data = pickle.load(f)
        
        date_ideas = data.get('date_ideas', [])
        embeddings = data.get('embeddings')
        model_name = data.get('model_name', 'all-MiniLM-L6-v2')
        
        logger.info(f"Loaded {len(date_ideas)} date ideas from {pickle_file}")
        return date_ideas, embeddings, model_name
        
    except Exception as e:
        logger.error(f"Failed to load {pickle_file}: {e}")
        return None, None, None

def migrate_data():
    """Migrate all pickle data to PostgreSQL"""
    logger.info("🚀 Starting migration from pickle files to PostgreSQL")
    
    # Test database connection
    if not test_connection():
        logger.error("❌ PostgreSQL connection failed. Please run init_database.py first.")
        return False
    
    # Find pickle files
    pickle_files = find_pickle_files()
    if not pickle_files:
        logger.warning("⚠️  No pickle files found to migrate")
        logger.info("Looking in:")
        data_dir = Path(__file__).parent / "data"
        logger.info(f"  - {data_dir}")
        return True
    
    logger.info(f"📁 Found {len(pickle_files)} pickle files:")
    for pf in pickle_files:
        logger.info(f"  - {pf}")
    
    # Create vector store instance
    vector_store = PostgreSQLVectorStore(use_fallback=False)
    
    all_date_ideas = []
    total_migrated = 0
    
    # Process each pickle file
    for pickle_file in pickle_files:
        logger.info(f"📦 Processing {pickle_file.name}...")
        
        date_ideas, embeddings, model_name = load_pickle_data(pickle_file)
        if date_ideas is None:
            continue
        
        # Ensure each date idea has an ID
        for i, idea in enumerate(date_ideas):
            if not idea.get("id"):
                idea["id"] = f"migrated_{pickle_file.stem}_{i}"
        
        all_date_ideas.extend(date_ideas)
        total_migrated += len(date_ideas)
        
        logger.info(f"✅ Loaded {len(date_ideas)} date ideas from {pickle_file.name}")
    
    if not all_date_ideas:
        logger.warning("⚠️  No date ideas found in pickle files")
        return True
    
    # Remove duplicates based on ID
    unique_ideas = {}
    for idea in all_date_ideas:
        unique_ideas[idea["id"]] = idea
    
    final_ideas = list(unique_ideas.values())
    
    if len(final_ideas) != len(all_date_ideas):
        logger.info(f"🔍 Removed {len(all_date_ideas) - len(final_ideas)} duplicates")
    
    # Add to PostgreSQL
    logger.info(f"💾 Migrating {len(final_ideas)} unique date ideas to PostgreSQL...")
    
    if vector_store.add_date_ideas(final_ideas):
        logger.info("✅ Migration completed successfully!")
        
        # Verify the data
        stats = vector_store.get_stats()
        logger.info(f"📊 Database stats: {stats}")
        
        # Test search
        logger.info("🔍 Testing search functionality...")
        test_results = vector_store.search("romantic dinner", top_k=3)
        logger.info(f"✅ Search test returned {len(test_results)} results")
        
        return True
    else:
        logger.error("❌ Migration failed!")
        return False

def backup_pickle_files():
    """Create backup of pickle files"""
    logger.info("💾 Creating backup of pickle files...")
    
    pickle_files = find_pickle_files()
    if not pickle_files:
        return
    
    backup_dir = Path(__file__).parent / "data" / "backup"
    backup_dir.mkdir(exist_ok=True)
    
    for pickle_file in pickle_files:
        backup_file = backup_dir / f"{pickle_file.stem}_backup{pickle_file.suffix}"
        
        try:
            import shutil
            shutil.copy2(pickle_file, backup_file)
            logger.info(f"✅ Backed up {pickle_file.name} to {backup_file}")
        except Exception as e:
            logger.error(f"❌ Failed to backup {pickle_file.name}: {e}")

def main():
    """Main function"""
    logger.info("🔄 AI Orchestrator Data Migration")
    logger.info("=" * 50)
    
    # Create backup first
    backup_pickle_files()
    
    # Perform migration
    if migrate_data():
        logger.info("🎉 Migration completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Test the application: python -m server.main")
        logger.info("2. Run tests: python -m pytest tests/")
        logger.info("3. Your pickle files are backed up in data/backup/")
        sys.exit(0)
    else:
        logger.error("💥 Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()