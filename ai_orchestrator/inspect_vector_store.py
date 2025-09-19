#!/usr/bin/env python3
"""
Inspect the contents of the vector store
"""
import json
import os
import sys

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from server.tools.vector_store import get_vector_store

def inspect_vector_store():
    """Inspect the contents of the vector store"""
    print("🔍 Vector Store Inspector")
    print("=" * 50)
    
    # Get vector store instance
    vs = get_vector_store()
    
    # Show stats
    print("\n📊 Statistics:")
    stats = vs.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Show all date ideas (from fallback file)
    print("\n📋 All Date Ideas in Vector Store:")
    print("-" * 40)
    
    # Load from the pickle file directly to see all contents
    import pickle
    fallback_file = os.path.join(os.path.dirname(__file__), "data", "date_ideas_vector_store.pkl")
    
    if os.path.exists(fallback_file):
        try:
            with open(fallback_file, "rb") as f:
                data = pickle.load(f)
            
            date_ideas = data.get("date_ideas", [])
            embeddings = data.get("embeddings")
            
            print(f"📚 Found {len(date_ideas)} date ideas:")
            print(f"🧠 Embeddings shape: {embeddings.shape if embeddings is not None else 'None'}")
            
            for i, idea in enumerate(date_ideas, 1):
                print(f"\n{i}. {idea.get('title', 'No title')}")
                print(f"   Description: {idea.get('description', 'No description')[:100]}...")
                print(f"   Categories: {', '.join(idea.get('categories', []))}")
                print(f"   City: {idea.get('city', 'No city')}")
                print(f"   Price Tier: {idea.get('price_tier', 'Unknown')}")
                print(f"   Duration: {idea.get('duration_min', 'Unknown')} min")
                print(f"   Indoor: {idea.get('indoor', 'Unknown')}")
                
        except Exception as e:
            print(f"❌ Error loading fallback file: {e}")
    else:
        print("❌ Fallback file not found")
    
    # Test some searches to see what's available
    print("\n🔍 Sample Searches:")
    print("-" * 30)
    
    test_queries = [
        "romantic",
        "outdoor",
        "food", 
        "adventure",
        "indoor",
        "cheap",
        "expensive"
    ]
    
    for query in test_queries:
        results = vs.search(query, top_k=3)
        print(f"\n'{query}' → {len(results)} results:")
        for j, result in enumerate(results[:2], 1):  # Show top 2
            similarity = result.get('similarity_score', 0)
            print(f"  {j}. {result['title']} ({similarity:.3f})")

def search_vector_store():
    """Interactive search of the vector store"""
    print("\n🔍 Interactive Vector Store Search")
    print("=" * 40)
    print("Enter search queries (type 'quit' to exit):")
    
    vs = get_vector_store()
    
    while True:
        try:
            query = input("\n🔍 Search: ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            if not query:
                continue
                
            results = vs.search(query, top_k=5)
            print(f"\n📍 Found {len(results)} results for '{query}':")
            
            for i, result in enumerate(results, 1):
                similarity = result.get('similarity_score', 0)
                source = result.get('source', 'unknown')
                print(f"\n{i}. {result['title']} (similarity: {similarity:.3f}, source: {source})")
                print(f"   Description: {result.get('description', 'No description')[:150]}...")
                print(f"   Categories: {', '.join(result.get('categories', []))}")
                print(f"   City: {result.get('city', 'Unknown')}")
                print(f"   Price: ${result.get('price_tier', '?')} tier")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n👋 Goodbye!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "search":
        search_vector_store()
    else:
        inspect_vector_store()
        
        # Ask if user wants interactive search
        try:
            response = input("\n🤔 Want to try interactive search? (y/n): ").strip().lower()
            if response in ['y', 'yes']:
                search_vector_store()
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")