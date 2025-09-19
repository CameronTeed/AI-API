#!/usr/bin/env python3
"""
REST API wrapper for the AI Orchestrator gRPC service
This provides a simple HTTP interface for easier integration
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import grpc
import chat_service_pb2
import chat_service_pb2_grpc
import uvicorn
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Orchestrator REST API",
    description="REST wrapper for the AI Orchestrator gRPC service",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str

class UserLocation(BaseModel):
    lat: float
    lon: float

class Constraints(BaseModel):
    city: Optional[str] = None
    budgetTier: Optional[int] = None  # 1, 2, 3
    hours: Optional[int] = None
    indoor: Optional[bool] = None
    categories: Optional[List[str]] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    userLocation: Optional[UserLocation] = None
    constraints: Optional[Constraints] = None

class EntityReference(BaseModel):
    id: str
    type: str
    title: str
    url: Optional[str] = None

class EntityReferences(BaseModel):
    primary_entity: EntityReference
    related_entities: List[EntityReference]

class Citation(BaseModel):
    url: str
    title: str

class Option(BaseModel):
    title: str
    categories: List[str]
    price: str
    duration_min: int
    why_it_fits: str
    logistics: str
    website: str
    source: str
    entity_references: Optional[EntityReferences] = None
    citations: List[Citation]

class ChatResponse(BaseModel):
    text: str
    structured: Optional[Dict[str, Any]] = None
    options: Optional[List[Option]] = None

# gRPC client setup
def get_grpc_stub():
    """Get gRPC stub for AI Orchestrator service"""
    try:
        channel = grpc.insecure_channel('localhost:50051')
        return chat_service_pb2_grpc.AiOrchestratorStub(channel)
    except Exception as e:
        logger.error(f"Failed to connect to gRPC service: {e}")
        raise HTTPException(status_code=503, detail="AI Orchestrator service unavailable")

def convert_entity_references(grpc_refs) -> Optional[EntityReferences]:
    """Convert gRPC EntityReferences to Pydantic model"""
    if not grpc_refs:
        return None
    
    primary = EntityReference(
        id=grpc_refs.primary_entity.id,
        type=grpc_refs.primary_entity.type,
        title=grpc_refs.primary_entity.title,
        url=grpc_refs.primary_entity.url if grpc_refs.primary_entity.url else None
    )
    
    related = [
        EntityReference(
            id=entity.id,
            type=entity.type,
            title=entity.title,
            url=entity.url if entity.url else None
        )
        for entity in grpc_refs.related_entities
    ]
    
    return EntityReferences(
        primary_entity=primary,
        related_entities=related
    )

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a chat request to the AI Orchestrator
    
    Returns both streaming text and structured response with entity references
    """
    try:
        stub = get_grpc_stub()
        
        # Convert to gRPC format
        grpc_messages = [
            chat_service_pb2.ChatMessage(role=msg.role, content=msg.content)
            for msg in request.messages
        ]
        
        grpc_request = chat_service_pb2.ChatRequest(
            messages=grpc_messages,
            stream=True
        )
        
        # Add optional fields
        if request.userLocation:
            grpc_request.userLocation.CopyFrom(
                chat_service_pb2.UserLocation(
                    lat=request.userLocation.lat,
                    lon=request.userLocation.lon
                )
            )
        
        if request.constraints:
            constraints = chat_service_pb2.Constraints()
            if request.constraints.city:
                constraints.city = request.constraints.city
            if request.constraints.budgetTier:
                constraints.budgetTier = request.constraints.budgetTier
            if request.constraints.hours:
                constraints.hours = request.constraints.hours
            if request.constraints.indoor is not None:
                constraints.indoor = request.constraints.indoor
            if request.constraints.categories:
                constraints.categories.extend(request.constraints.categories)
            
            grpc_request.constraints.CopyFrom(constraints)
        
        # Get streaming response
        response_stream = stub.Chat(iter([grpc_request]))
        
        full_text = ""
        structured_data = None
        options = []
        
        for response in response_stream:
            if response.text_delta:
                full_text += response.text_delta
            
            if response.structured:
                structured_data = response.structured
                
                # Convert options
                for option in response.structured.options:
                    citations = [
                        Citation(url=cite.url, title=cite.title)
                        for cite in option.citations
                    ]
                    
                    entity_refs = convert_entity_references(option.entity_references)
                    
                    options.append(Option(
                        title=option.title,
                        categories=list(option.categories),
                        price=option.price,
                        duration_min=option.duration_min,
                        why_it_fits=option.why_it_fits,
                        logistics=option.logistics,
                        website=option.website,
                        source=option.source,
                        entity_references=entity_refs,
                        citations=citations
                    ))
            
            if response.done:
                break
        
        # Prepare response
        response_data = ChatResponse(
            text=full_text,
            options=options
        )
        
        if structured_data:
            response_data.structured = {
                "summary": structured_data.summary,
                "options_count": len(options)
            }
        
        return response_data
        
    except grpc.RpcError as e:
        logger.error(f"gRPC error: {e}")
        raise HTTPException(status_code=500, detail=f"AI service error: {e.details()}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        stub = get_grpc_stub()
        
        # Test basic connection
        test_request = chat_service_pb2.ChatRequest(
            messages=[
                chat_service_pb2.ChatMessage(role="user", content="ping")
            ],
            stream=True
        )
        
        response_stream = stub.Chat(iter([test_request]))
        
        # Just check if we get a response
        next(response_stream)
        
        return {"status": "healthy", "service": "AI Orchestrator"}
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/api/status")
async def get_status():
    """Get service status and statistics"""
    try:
        # You can add vector store statistics here
        from server.tools.vector_store import get_vector_store
        
        vector_store = get_vector_store()
        stats = vector_store.get_stats()
        
        return {
            "status": "running",
            "vector_store": stats,
            "endpoints": {
                "chat": "/api/chat",
                "health": "/api/health",
                "docs": "/docs"
            }
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "status": "degraded",
            "error": str(e)
        }

# Example usage endpoint
@app.get("/api/example")
async def get_example():
    """Get example request format"""
    return {
        "example_request": {
            "messages": [
                {
                    "role": "user",
                    "content": "I want a romantic date idea in New York for around $50"
                }
            ],
            "constraints": {
                "city": "New York",
                "budgetTier": 2,
                "categories": ["romantic"]
            },
            "userLocation": {
                "lat": 40.7128,
                "lon": -74.0060
            }
        },
        "example_response": {
            "text": "Here are some great romantic date ideas in New York...",
            "structured": {
                "summary": "Romantic date options in NYC within budget",
                "options_count": 3
            },
            "options": [
                {
                    "title": "Art Museum Visit",
                    "categories": ["romantic", "cultural"],
                    "price": "$$",
                    "duration_min": 180,
                    "why_it_fits": "Perfect for couples who love art...",
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
    }

if __name__ == "__main__":
    uvicorn.run(
        "rest_api_wrapper:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
