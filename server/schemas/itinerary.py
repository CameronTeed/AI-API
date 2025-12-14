"""
Itinerary schemas with explanation metadata.

Stores why each plan was chosen, making AI decisions interpretable.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class VenueExplanation(BaseModel):
    """Explanation for why a specific venue was chosen"""
    venue_id: str
    venue_name: str
    
    # Scoring breakdown
    vibe_match_score: float  # 0-100: How well it matches the vibe
    budget_fit_score: float  # 0-100: How well it fits budget
    distance_score: float    # 0-100: Distance efficiency
    rating_score: float      # 0-100: Based on reviews
    diversity_score: float   # 0-100: Adds variety to itinerary
    
    # Overall
    total_fitness_score: float  # 0-1000: GA fitness score
    
    # Human-readable explanation
    why_chosen: str  # "Highly rated romantic restaurant with great reviews"
    alternatives_rejected: List[str] = []  # Why other venues weren't chosen


class ItineraryExplanation(BaseModel):
    """Explanation for entire itinerary"""
    
    # Overall metrics
    total_fitness_score: float  # GA fitness score
    vibe_match_score: float     # 0-100: Overall vibe match
    budget_fit_score: float     # 0-100: Budget adherence
    flow_score: float           # 0-100: Logical date flow
    diversity_score: float      # 0-100: Variety of activities
    
    # Breakdown
    venue_explanations: List[VenueExplanation]
    
    # Summary
    summary: str  # "Perfect romantic evening with great flow and budget fit"
    
    # Algorithm info
    algorithm_used: str  # "genetic_algorithm" or "heuristic"
    optimization_iterations: Optional[int] = None  # For GA
    
    # Constraints applied
    constraints_applied: Dict[str, Any] = {}  # {"vibe": "romantic", "budget": 150}


class DatePlan(BaseModel):
    """Complete date plan with venues and explanation"""
    
    plan_id: str
    created_at: datetime
    
    # Venues in order
    venues: List[Dict[str, Any]]  # Full venue data
    
    # Explanation
    explanation: ItineraryExplanation
    
    # Metadata
    total_duration_minutes: int
    total_estimated_cost: float
    vibe: str
    
    # For partial regeneration
    locked_constraints: Dict[str, Any] = {}  # Constraints user locked
    regeneration_history: List[Dict[str, Any]] = []  # Previous versions


class PartialRegenerationRequest(BaseModel):
    """Request to regenerate part of a plan"""
    
    plan_id: str
    
    # Which venue to regenerate (by index)
    venue_index: int
    
    # Constraints to lock
    lock_budget: bool = False
    lock_vibe: bool = False
    lock_duration: bool = False
    
    # Optional: new constraints
    new_budget: Optional[float] = None
    new_vibe: Optional[str] = None
    new_duration: Optional[int] = None

