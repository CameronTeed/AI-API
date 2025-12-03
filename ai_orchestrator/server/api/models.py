"""
Pydantic models for API requests and responses
"""

from typing import List, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """A single chat message"""
    role: str  # 'user', 'assistant', 'system'
    content: str


class Location(BaseModel):
    """User location coordinates"""
    lat: float
    lon: float


class Constraints(BaseModel):
    """Constraints for date idea search"""
    city: Optional[str] = None
    budget_tier: Optional[int] = None  # 1-3
    hours: Optional[int] = None
    indoor: Optional[bool] = None
    categories: Optional[List[str]] = None


class ChatRequest(BaseModel):
    """Request for chat endpoint"""
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    messages: List[ChatMessage]
    constraints: Optional[Constraints] = None
    user_location: Optional[Location] = None


class ChatResponse(BaseModel):
    """Response from chat endpoint"""
    session_id: str
    response: str
    suggestions: Optional[List[str]] = None


class Option(BaseModel):
    """A date idea option"""
    title: str
    categories: List[str]
    price: str
    duration_min: int
    why_it_fits: str
    logistics: str
    website: str
    source: str


class StructuredAnswer(BaseModel):
    """Structured answer with date ideas"""
    summary: str
    options: List[Option]

