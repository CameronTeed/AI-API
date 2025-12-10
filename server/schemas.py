from typing import List, Optional
from pydantic import BaseModel

class EntityReference(BaseModel):
    id: str
    type: str  # date_idea, venue, city, category, price_tier, business
    title: str
    url: Optional[str] = None

class EntityReferences(BaseModel):
    primary_entity: EntityReference
    related_entities: List[EntityReference]

class DateIdea(BaseModel):
    id: str
    title: str
    description: str
    categories: List[str]
    city: str
    lat: float
    lon: float
    price_tier: int
    duration_min: int
    indoor: bool
    kid_friendly: bool
    website: str
    phone: str
    open_hours_json: str
    rating: float
    review_count: int
    updated_at: str
    entity_references: Optional[EntityReferences] = None

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

class StructuredAnswer(BaseModel):
    summary: str
    options: List[Option]

class WebSearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    published_at: Optional[str] = None
