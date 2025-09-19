#!/usr/bin/env python3
"""
Initialize the vector store with sample date ideas
"""
import json
import os
import sys

# Add the parent directory to the path so we can import the server modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.tools.vector_store import DateIdeaVectorStore

def initialize_vector_store():
    """Initialize the vector store with sample date ideas"""
    
    # Path to sample data
    sample_data_path = os.path.join(
        os.path.dirname(__file__), 
        "data/sample_date_ideas.json"
    )
    
    if not os.path.exists(sample_data_path):
        print(f"❌ Sample data not found at: {sample_data_path}")
        return False
    
    print("🚀 Initializing vector store...")
    
    # Load sample data
    try:
        with open(sample_data_path, 'r') as f:
            sample_data = json.load(f)
        
        print(f"📚 Loaded {len(sample_data)} sample date ideas")
        
    except Exception as e:
        print(f"❌ Failed to load sample data: {e}")
        return False
    
    # Initialize vector store
    try:
        vector_store = DateIdeaVectorStore()
        
        # Add the sample data
        vector_store.add_date_ideas(sample_data)
        
        print("✅ Vector store initialized successfully!")
        
        # Print stats
        stats = vector_store.get_stats()
        print(f"📊 Stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize vector store: {e}")
        return False

if __name__ == "__main__":
    success = initialize_vector_store()
    if success:
        print("\n🎉 Vector store is ready! You can now start the server.")
    else:
        print("\n💥 Failed to initialize vector store.")
        sys.exit(1)
