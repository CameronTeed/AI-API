# seed_database.py
# Script to populate PostgreSQL database with venue data from Google Places API
# Handles vibe classification, embeddings, and smart caching

import os
import sys
import pandas as pd
from dotenv import load_dotenv
import db_manager
import nlp_classifier
import fetch_real_data

load_dotenv()

def seed_from_api(api_key: str = None):
    """Fetch data from Google Places API and seed database"""
    api_key = api_key or os.getenv('GOOGLE_PLACES_API_KEY')
    
    if not api_key:
        print("✗ GOOGLE_PLACES_API_KEY not set")
        return False
    
    print("\n" + "="*70)
    print("SEEDING DATABASE FROM GOOGLE PLACES API")
    print("="*70)
    
    # Initialize database
    print("\n1. Initializing database...")
    db_manager.init_db_pool()
    db_manager.init_embedding_model()
    db_manager.create_tables()
    
    # Fetch data from API
    print("\n2. Fetching venue data from Google Places API...")
    print("   This may take a few minutes...")
    venues = []
    
    for query in fetch_real_data.SEARCH_QUERIES:
        places = fetch_real_data.fetch_places(query, api_key)
        venues.extend(places)
    
    if not venues:
        print("✗ No venues fetched from API")
        return False
    
    print(f"\n✓ Fetched {len(venues)} venues from API")
    
    # Classify vibes
    print("\n3. Classifying vibes for venues...")
    for i, venue in enumerate(venues):
        if i % 50 == 0:
            print(f"   Processing {i}/{len(venues)}...")
        
        text = f"{venue.get('description', '')} {venue.get('review', '')} {venue.get('type', '')}"
        vibes = nlp_classifier.get_keyword_vibes(text)
        venue['true_vibe'] = ", ".join(vibes) if vibes else 'casual'
    
    print(f"✓ Classified vibes for {len(venues)} venues")
    
    # Insert into database
    print("\n4. Inserting venues into database...")
    inserted = db_manager.insert_venues(venues)
    
    if inserted > 0:
        print(f"✓ Successfully seeded database with {inserted} venues")
        return True
    else:
        print("✗ Failed to insert venues")
        return False

def seed_from_csv(csv_path: str = 'ottawa_venues.csv'):
    """Seed database from existing CSV file"""
    if not os.path.exists(csv_path):
        print(f"✗ CSV file not found: {csv_path}")
        return False
    
    print("\n" + "="*70)
    print(f"SEEDING DATABASE FROM CSV: {csv_path}")
    print("="*70)
    
    # Initialize database
    print("\n1. Initializing database...")
    db_manager.init_db_pool()
    db_manager.init_embedding_model()
    db_manager.create_tables()
    
    # Load CSV
    print(f"\n2. Loading venues from {csv_path}...")
    df = pd.read_csv(csv_path)
    venues = df.to_dict('records')
    print(f"✓ Loaded {len(venues)} venues from CSV")
    
    # Insert into database
    print("\n3. Inserting venues into database...")
    inserted = db_manager.insert_venues(venues)
    
    if inserted > 0:
        print(f"✓ Successfully seeded database with {inserted} venues")
        return True
    else:
        print("✗ Failed to insert venues")
        return False

def verify_database():
    """Verify database was seeded correctly"""
    print("\n" + "="*70)
    print("VERIFYING DATABASE")
    print("="*70)
    
    db_manager.init_db_pool()
    
    # Get all venues
    df = db_manager.get_all_venues()
    
    if df.empty:
        print("✗ Database is empty")
        return False
    
    print(f"\n✓ Database contains {len(df)} venues")
    print(f"\nVenue Statistics:")
    print(f"  - Average rating: {df['rating'].mean():.2f}")
    print(f"  - Average cost: ${df['cost'].mean():.2f}")
    print(f"  - Vibes: {df['true_vibe'].nunique()} unique")
    print(f"  - Types: {df['type'].nunique()} unique")
    
    # Sample venues
    print(f"\nSample venues:")
    for idx, row in df.head(5).iterrows():
        print(f"  - {row['name']} ({row['type']}) - ${row['cost']} - ⭐{row['rating']}")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed database with venue data")
    parser.add_argument('--api', action='store_true', help='Fetch from Google Places API')
    parser.add_argument('--csv', type=str, help='Load from CSV file')
    parser.add_argument('--verify', action='store_true', help='Verify database')
    
    args = parser.parse_args()
    
    if args.api:
        success = seed_from_api()
    elif args.csv:
        success = seed_from_csv(args.csv)
    else:
        # Default: try CSV first, then API
        if os.path.exists('ottawa_venues.csv'):
            success = seed_from_csv()
        else:
            success = seed_from_api()
    
    if success and (args.verify or not args.api and not args.csv):
        verify_database()
    
    db_manager.close_pool()
    sys.exit(0 if success else 1)

