#!/usr/bin/env python3
"""
Migration script to add opening hours columns to venues table
Run this once to update the database schema
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate():
    """Add opening hours columns to venues table"""

    # Get connection details from environment
    # Load from parent directory .env first
    parent_env = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(parent_env):
        load_dotenv(parent_env)

    host = os.getenv('DB_HOST', 'localhost')
    database = os.getenv('DB_NAME', 'sparkdates')
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', 'postgres')
    port = int(os.getenv('DB_PORT', 5432))
    
    conn = None
    cur = None
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port
        )
        cur = conn.cursor()
        
        print("🔄 Checking if columns exist...")
        
        # Check if columns already exist
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='venues' 
            AND column_name IN ('regular_opening_hours', 'current_opening_hours')
        """)
        existing = [row[0] for row in cur.fetchall()]
        
        if 'regular_opening_hours' not in existing:
            print("➕ Adding regular_opening_hours column...")
            cur.execute("""
                ALTER TABLE venues 
                ADD COLUMN regular_opening_hours TEXT DEFAULT ''
            """)
            print("✓ Added regular_opening_hours")
        else:
            print("✓ regular_opening_hours already exists")
        
        if 'current_opening_hours' not in existing:
            print("➕ Adding current_opening_hours column...")
            cur.execute("""
                ALTER TABLE venues 
                ADD COLUMN current_opening_hours TEXT DEFAULT ''
            """)
            print("✓ Added current_opening_hours")
        else:
            print("✓ current_opening_hours already exists")
        
        conn.commit()
        print("\n✅ Migration complete!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate()

