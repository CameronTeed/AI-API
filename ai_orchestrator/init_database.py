#!/usr/bin/env python3
"""
Initialize the PostgreSQL database with schema and extensions
"""
import os
import sys
import logging
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file")
except ImportError:
    print("Warning: python-dotenv not available. Make sure to set environment variables manually.")

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from server.db_config import get_db_config, test_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_sql_file(file_path: str) -> str:
    """Read SQL file contents"""
    with open(file_path, 'r') as f:
        return f.read()

def apply_flyway_migrations(config):
    """Apply Flyway migrations in order"""
    logger.info("🔄 Applying Flyway migrations...")
    
    flyway_dir = Path(__file__).parent / "flyway"
    if not flyway_dir.exists():
        logger.warning("⚠️  No flyway directory found")
        return True
    
    # Get all migration files in order
    migration_files = sorted([f for f in flyway_dir.glob("V*.sql")])
    
    if not migration_files:
        logger.info("📄 No migration files found")
        return True
    
    try:
        with config.get_connection() as conn:
            with conn.cursor() as cur:
                # Create flyway_schema_history table if it doesn't exist
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS flyway_schema_history (
                        installed_rank INTEGER NOT NULL,
                        version VARCHAR(50),
                        description VARCHAR(200),
                        type VARCHAR(20) NOT NULL,
                        script VARCHAR(1000) NOT NULL,
                        checksum INTEGER,
                        installed_by VARCHAR(100) NOT NULL,
                        installed_on TIMESTAMP NOT NULL DEFAULT NOW(),
                        execution_time INTEGER NOT NULL,
                        success BOOLEAN NOT NULL,
                        PRIMARY KEY (installed_rank)
                    );
                """)
                
                for migration_file in migration_files:
                    script_name = migration_file.name
                    
                    # Check if migration was already applied
                    cur.execute(
                        "SELECT 1 FROM flyway_schema_history WHERE script = %s AND success = true",
                        (script_name,)
                    )
                    
                    if cur.fetchone():
                        logger.info(f"⏩ Skipping already applied migration: {script_name}")
                        continue
                    
                    logger.info(f"📄 Applying migration: {script_name}")
                    
                    # Read and execute migration
                    migration_sql = read_sql_file(migration_file)
                    
                    try:
                        import time
                        start_time = time.time()
                        cur.execute(migration_sql)
                        execution_time = int((time.time() - start_time) * 1000)
                        
                        # Record successful migration
                        cur.execute("""
                            INSERT INTO flyway_schema_history 
                            (installed_rank, version, description, type, script, installed_by, execution_time, success)
                            VALUES 
                            ((SELECT COALESCE(MAX(installed_rank), 0) + 1 FROM flyway_schema_history), 
                             %s, %s, 'SQL', %s, 'init_database.py', %s, true)
                        """, (
                            script_name.split('__')[0].replace('V', '').replace('_', '.'),
                            script_name.split('__')[1].replace('.sql', '').replace('_', ' '),
                            script_name,
                            execution_time
                        ))
                        
                        logger.info(f"✅ Applied migration: {script_name}")
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to apply migration {script_name}: {e}")
                        # Record failed migration
                        cur.execute("""
                            INSERT INTO flyway_schema_history 
                            (installed_rank, version, description, type, script, installed_by, execution_time, success)
                            VALUES 
                            ((SELECT COALESCE(MAX(installed_rank), 0) + 1 FROM flyway_schema_history), 
                             %s, %s, 'SQL', %s, 'init_database.py', 0, false)
                        """, (
                            script_name.split('__')[0].replace('V', '').replace('_', '.'),
                            script_name.split('__')[1].replace('.sql', '').replace('_', ' '),
                            script_name
                        ))
                        return False
                
                conn.commit()
                logger.info("✅ All migrations applied successfully!")
                return True
                
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

def initialize_database():
    """Initialize the database with schema and extensions"""
    logger.info("🚀 Initializing database...")
    
    # Test connection first
    if not test_connection():
        logger.error("❌ Database connection failed. Please check your configuration.")
        logger.info("Environment variables to set:")
        logger.info("  DB_HOST (default: localhost)")
        logger.info("  DB_PORT (default: 5432)")
        logger.info("  DB_NAME (default: ai_orchestrator)")
        logger.info("  DB_USER (default: postgres)")
        logger.info("  DB_PASSWORD (default: postgres)")
        return False
    
    config = get_db_config()
    
    # Read schema file
    schema_path = Path(__file__).parent / "sql" / "schema.sql"
    if not schema_path.exists():
        logger.error(f"❌ Schema file not found: {schema_path}")
        return False
    
    schema_sql = read_sql_file(schema_path)
    
    try:
        with config.get_connection() as conn:
            with conn.cursor() as cur:
                logger.info("📦 Creating pgvector extension...")
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                logger.info("🏗️  Creating schema...")
                # Execute the schema in parts to handle potential issues
                statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                
                for i, statement in enumerate(statements):
                    if statement:
                        try:
                            cur.execute(statement + ';')
                            logger.debug(f"✅ Executed statement {i+1}/{len(statements)}")
                        except Exception as e:
                            # Some statements might fail if they already exist, which is OK
                            logger.debug(f"⚠️  Statement {i+1} warning: {e}")
                
                conn.commit()
                logger.info("✅ Database initialization completed successfully!")
                
                # Verify tables were created
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'date_ideas'
                """)
                if cur.fetchone():
                    logger.info("✅ date_ideas table created successfully")
                else:
                    logger.warning("⚠️  date_ideas table not found")
                
                # Check for pgvector extension
                cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector'")
                if cur.fetchone():
                    logger.info("✅ pgvector extension is active")
                else:
                    logger.error("❌ pgvector extension not found")
                    return False
                
        # Apply Flyway migrations
        if not apply_flyway_migrations(config):
            logger.error("❌ Failed to apply migrations")
            return False
                
        return True
                
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

def main():
    """Main function"""
    logger.info("🔧 AI Orchestrator Database Initialization")
    logger.info("=" * 50)
    
    if initialize_database():
        logger.info("🎉 Database is ready!")
        logger.info("\nNext steps:")
        logger.info("1. Install dependencies: pip install -r requirements.txt")
        logger.info("2. Populate vector store: python populate_vector_store.py")
        logger.info("3. Run tests: python -m pytest tests/")
        sys.exit(0)
    else:
        logger.error("💥 Database initialization failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()