# Backend Integration Instructions

## Quick Start Guide

### 1. Setup and Installation

```bash
# Clone/navigate to your ai_orchestrator directory
cd /path/to/ai_orchestrator

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Populate the vector store with sample data
python3 populate_vector_store.py

# Test the integration
python3 test_entity_references.py
python3 test_backend_integration.py

# Start the gRPC server
python3 -m server.main
```

### 2. Environment Variables

Create a `.env` file in the ai_orchestrator directory:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional
LOG_LEVEL=INFO
GRPC_PORT=50051
```

## Integration Options

### Option 1: Direct gRPC Integration (Recommended)

Use the gRPC service directly for best performance:

```python
import grpc
import chat_service_pb2
import chat_service_pb2_grpc

# Connect to service
channel = grpc.insecure_channel('localhost:50051')
stub = chat_service_pb2_grpc.AiOrchestratorStub(channel)

# Create request
request = chat_service_pb2.ChatRequest(
    messages=[
        chat_service_pb2.ChatMessage(
            role="user",
            content="I want a romantic date in NYC under $75"
        )
    ],
    constraints=chat_service_pb2.Constraints(
        city="New York",
        budgetTier=2,
        categories=["romantic"]
    )
)

# Get streaming response with entity references
for response in stub.Chat(iter([request])):
    if response.text_delta:
        print(response.text_delta, end='')
    
    if response.structured:
        for option in response.structured.options:
            # Process entity references for clickable keywords
            entity_refs = option.entity_references
            print(f"Primary: {entity_refs.primary_entity.title}")
            for entity in entity_refs.related_entities:
                print(f"Related: {entity.type} - {entity.title} -> {entity.url}")
```

### Option 2: REST API Wrapper (Easier Integration)

Use the provided REST API wrapper for HTTP-based integration:

```bash
# Start both services
python3 -m server.main &  # gRPC service on port 50051
python3 rest_api_wrapper.py &  # REST API on port 8000
```

Then use standard HTTP requests:

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "romantic date in NYC under $75"}
    ],
    "constraints": {
      "city": "New York",
      "budgetTier": 2,
      "categories": ["romantic"]
    }
  }'
```

Response includes entity references:
```json
{
  "text": "Here are some romantic date ideas...",
  "options": [
    {
      "title": "Art Museum Visit",
      "entity_references": {
        "primary_entity": {
          "id": "date_idea_002",
          "type": "date_idea",
          "title": "Art Museum Visit",
          "url": "/api/date-ideas/date_idea_002"
        },
        "related_entities": [
          {
            "id": "venue_met_museum_001",
            "type": "venue",
            "title": "Metropolitan Museum of Art",
            "url": "/api/venues/venue_met_museum_001"
          }
        ]
      }
    }
  ]
}
```

## Testing Your Integration

### 1. Test Basic Connection
```bash
python3 test_backend_integration.py
```

### 2. Test REST API (if using Option 2)
```bash
# Health check
curl http://localhost:8000/api/health

# Get example request format
curl http://localhost:8000/api/example

# Interactive docs
open http://localhost:8000/docs
```

### 3. Test Entity References
```bash
python3 test_entity_references.py
```

## Complete gRPC Example

```python
#!/usr/bin/env python3
"""
Complete example of using the AI orchestrator backend
"""
import grpc
import chat_service_pb2
import chat_service_pb2_grpc

def main():
    # Connect to server
    channel = grpc.insecure_channel('localhost:50051')
    stub = chat_service_pb2_grpc.AiOrchestratorStub(channel)
    
    # Create request
    messages = [
        chat_service_pb2.ChatMessage(
            role="user", 
            content="I want a fun date idea in Chicago for under $50"
        )
    ]
    
    constraints = chat_service_pb2.Constraints(
        city="Chicago",
        budgetTier=1,  # Budget-friendly
        categories=["fun", "casual"]
    )
    
    request = chat_service_pb2.ChatRequest(
        messages=messages,
        constraints=constraints,
        stream=True
    )
    
    # Send request and process response
    try:
        response_stream = stub.Chat(iter([request]))
        
        full_text = ""
        
        for response in response_stream:
            if response.text_delta:
                full_text += response.text_delta
                print(response.text_delta, end='', flush=True)
            
            if response.structured:
                print(f"\n\nStructured Response:")
                print(f"Summary: {response.structured.summary}")
                
                for i, option in enumerate(response.structured.options, 1):
                    print(f"\n--- Option {i}: {option.title} ---")
                    print(f"Categories: {', '.join(option.categories)}")
                    print(f"Price: {option.price}")
                    print(f"Duration: {option.duration_min} minutes")
                    print(f"Source: {option.source}")
                    
                    # Entity references for clickable keywords
                    if option.entity_references:
                        refs = option.entity_references
                        print(f"Primary Entity: {refs.primary_entity.title} ({refs.primary_entity.type})")
                        print(f"Related Entities: {len(refs.related_entities)}")
                        
                        for entity in refs.related_entities:
                            print(f"  - {entity.type}: {entity.title} -> {entity.url}")
            
            if response.done:
                print("\n\nResponse completed!")
                break
                
    except grpc.RpcError as e:
        print(f"gRPC error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        channel.close()

if __name__ == "__main__":
    main()
```

## Required API Endpoints in Your Main Backend

Implement these endpoints to serve entity data that users click on:

### Date Ideas
```python
@app.get("/api/date-ideas/{date_idea_id}")
async def get_date_idea(date_idea_id: str):
    return {
        "id": date_idea_id,
        "title": "Art Museum Visit",
        "description": "...",
        "categories": ["cultural", "art"],
        "city": "New York",
        "venue": {...},
        "business": {...},
        "similar_ideas": [...],
        "reviews": [...]
    }
```

### Venues
```python
@app.get("/api/venues/{venue_id}")
async def get_venue(venue_id: str):
    return {
        "id": venue_id,
        "name": "Metropolitan Museum of Art",
        "address": "1000 5th Ave, New York, NY",
        "hours": {...},
        "contact": {...},
        "related_date_ideas": [...],
        "photos": [...],
        "amenities": [...]
    }
```

### Cities
```python
@app.get("/api/cities/{city_id}")
async def get_city(city_id: str):
    return {
        "id": city_id,
        "name": "New York",
        "state": "NY",
        "country": "USA",
        "popular_venues": [...],
        "date_ideas_count": 150,
        "top_categories": [...],
        "neighborhoods": [...]
    }
```

### Categories
```python
@app.get("/api/categories/{category_id}")
async def get_category(category_id: str):
    return {
        "id": category_id,
        "name": "romantic",
        "description": "Perfect for couples...",
        "related_categories": [...],
        "popular_date_ideas": [...],
        "cities_with_options": [...],
        "average_price": "$$"
    }
```

### Price Tiers
```python
@app.get("/api/price-tiers/{tier}")
async def get_price_tier(tier: int):
    return {
        "tier": tier,
        "symbol": "$" if tier == 1 else "$$" if tier == 2 else "$$$",
        "range": "Under $25" if tier == 1 else "$25-75" if tier == 2 else "$75+",
        "date_ideas_count": 50,
        "popular_activities": [...],
        "cities": [...]
    }
```

### Businesses
```python
@app.get("/api/businesses/{business_id}")
async def get_business(business_id: str):
    return {
        "id": business_id,
        "name": "The Met",
        "type": "museum",
        "venues": [...],
        "date_ideas": [...],
        "contact": {...},
        "social_media": {...}
    }
```

## Data Management

### Adding New Date Ideas

1. **Add to your database and create JSON entry**:
```json
{
  "id": "date_idea_011",
  "title": "Wine and Paint Night",
  "description": "Creative date combining art and wine",
  "categories": ["creative", "romantic", "indoor"],
  "city": "San Francisco",
  "city_id": "san_francisco",
  "venue_id": "venue_paint_studio_001",
  "venue_name": "Artsy Studio",
  "business_id": "business_artsy_001",
  "business_name": "Artsy Entertainment",
  "price_tier": 2,
  "duration_min": 120,
  "indoor": true,
  "kid_friendly": false,
  "website": "https://artsystudio.com",
  "phone": "+1-415-555-0123",
  "lat": 37.7749,
  "lon": -122.4194,
  "rating": 4.5,
  "review_count": 89
}
```

2. **Update vector store**:
```bash
python3 populate_vector_store.py
```

### Bulk Data Import

Create a custom import script for your existing database:

```python
#!/usr/bin/env python3
"""
Import date ideas from your existing database to vector store
"""
import json
from server.tools.vector_store import get_vector_store

def import_from_your_database():
    # Connect to your existing database
    # db = connect_to_your_db()
    
    # Fetch all date ideas with relationships
    # date_ideas = db.execute("""
    #     SELECT di.*, v.name as venue_name, b.name as business_name, c.name as city_name
    #     FROM date_ideas di
    #     LEFT JOIN venues v ON di.venue_id = v.id
    #     LEFT JOIN businesses b ON di.business_id = b.id
    #     LEFT JOIN cities c ON di.city_id = c.id
    # """)
    
    # Transform to vector store format
    transformed_ideas = []
    for idea in date_ideas:
        transformed = {
            "id": f"date_idea_{idea['id']}",
            "title": idea['title'],
            "description": idea['description'],
            "categories": idea['categories'].split(',') if idea['categories'] else [],
            "city": idea['city_name'] or idea['city'],
            "city_id": idea['city'].lower().replace(' ', '_'),
            "venue_id": f"venue_{idea['venue_id']}" if idea['venue_id'] else None,
            "venue_name": idea['venue_name'],
            "business_id": f"business_{idea['business_id']}" if idea['business_id'] else None,
            "business_name": idea['business_name'],
            "price_tier": idea['price_tier'],
            "duration_min": idea['duration_minutes'],
            "indoor": idea['is_indoor'],
            "kid_friendly": idea['is_kid_friendly'],
            "website": idea['website'],
            "phone": idea['phone'],
            "lat": idea['latitude'],
            "lon": idea['longitude'],
            "rating": idea['rating'],
            "review_count": idea['review_count']
        }
        transformed_ideas.append(transformed)
    
    # Add to vector store
    vector_store = get_vector_store()
    vector_store.add_date_ideas(transformed_ideas)
    
    print(f"Imported {len(transformed_ideas)} date ideas to vector store")

if __name__ == "__main__":
    import_from_your_database()
```

## Production Deployment

### 1. Docker Configuration

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Populate vector store during build
RUN python3 populate_vector_store.py

EXPOSE 50051 8000

# Start both gRPC and REST services
CMD ["python3", "-m", "server.main"]
```

### 2. Load Balancing

For high traffic, run multiple instances:

```yaml
# docker-compose.yml
version: '3.8'

services:
  ai-orchestrator-1:
    build: .
    ports:
      - "50051:50051"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
  
  ai-orchestrator-2:
    build: .
    ports:
      - "50052:50051"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
  
  nginx:
    image: nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### 3. Monitoring

Add health checks and metrics:

```python
# In your main backend
@app.get("/api/ai-orchestrator/health")
async def check_ai_orchestrator():
    try:
        channel = grpc.insecure_channel('localhost:50051')
        stub = chat_service_pb2_grpc.AiOrchestratorStub(channel)
        # Test connection
        return {"status": "healthy"}
    except:
        return {"status": "unhealthy"}
```

## Performance Optimization

### 1. Vector Store Optimization
- Preload vector store at startup
- Use batch processing for multiple requests
- Cache frequently accessed entities

### 2. gRPC Optimization
- Use connection pooling
- Enable gRPC compression
- Set appropriate timeouts

### 3. Memory Management
- Monitor vector store memory usage
- Implement periodic cleanup
- Use efficient data structures

That's it! Your backend is now ready to use the enhanced AI orchestrator with clickable entity references. The system will automatically generate structured responses with database object references that your frontend can render as interactive elements.
