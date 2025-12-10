#!/usr/bin/env python3
"""
Simple script to seed database with sample data
Run this to quickly populate the database with pre-curated date ideas
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.seed_from_json import JSONDatabaseSeeder

def main():
    """Seed database with sample data"""
    
    # Database configuration from environment
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'sparkdates_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres'),
    }
    
    # Path to sample data
    sample_file = Path(__file__).parent.parent / 'data' / 'sample_date_ideas.json'
    
    if not sample_file.exists():
        print(f"❌ Sample data file not found: {sample_file}")
        sys.exit(1)
    
    print("🌱 Seeding SparkDates database with sample data...")
    print(f"📂 Using: {sample_file}")
    print()
    
    try:
        seeder = JSONDatabaseSeeder(db_config)
        seeder.seed_from_json(str(sample_file))
        print()
        print("✅ Sample data seeding completed successfully!")
        print()
        print("Next steps:")
        print("  1. Start the backend: cd api && ./gradlew bootRun")
        print("  2. Test the API: curl http://localhost:8081/api/health")
        print("  3. Try a search: curl -X POST http://localhost:8081/api/ai/chat/stream ...")
        
    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

