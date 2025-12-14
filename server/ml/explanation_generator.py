"""
Explanation Generator - Makes AI decisions interpretable.

Computes scores for:
- Vibe match
- Budget fit
- Distance/time efficiency
- GA fitness
- Diversity

Generates human-readable explanations for each venue choice.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import math

logger = logging.getLogger(__name__)


class ExplanationGenerator:
    """Generates interpretable explanations for date plans"""
    
    @staticmethod
    def generate_itinerary_explanation(
        venues: List[Dict[str, Any]],
        target_vibe: str,
        budget_limit: float,
        ga_fitness_score: float,
        algorithm_used: str = "genetic_algorithm",
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate explanation for entire itinerary.
        
        Args:
            venues: List of venues in the plan
            target_vibe: Target vibe (romantic, adventurous, etc)
            budget_limit: Budget limit in dollars
            ga_fitness_score: GA fitness score (0-1000)
            algorithm_used: "genetic_algorithm" or "heuristic"
            constraints: Applied constraints
            
        Returns:
            Explanation dict with all scores and reasoning
        """
        
        # Calculate individual venue explanations
        venue_explanations = []
        total_cost = 0
        
        for i, venue in enumerate(venues):
            vibe_match = ExplanationGenerator._calculate_vibe_match(venue, target_vibe)
            budget_fit = ExplanationGenerator._calculate_budget_fit(venue, budget_limit, i, len(venues))
            distance_score = ExplanationGenerator._calculate_distance_score(venue, i, venues)
            rating_score = ExplanationGenerator._calculate_rating_score(venue)
            diversity_score = ExplanationGenerator._calculate_diversity_score(venue, i, venues)
            
            total_cost += venue.get('price_tier', 1) * 30  # Estimate cost
            
            venue_exp = {
                "venue_id": venue.get('id', f"venue_{i}"),
                "venue_name": venue.get('name', 'Unknown Venue'),
                "vibe_match_score": vibe_match,
                "budget_fit_score": budget_fit,
                "distance_score": distance_score,
                "rating_score": rating_score,
                "diversity_score": diversity_score,
                "total_fitness_score": ga_fitness_score / len(venues),  # Approximate per-venue
                "why_chosen": ExplanationGenerator._generate_venue_explanation(
                    venue, vibe_match, budget_fit, distance_score, rating_score
                ),
                "alternatives_rejected": []
            }
            venue_explanations.append(venue_exp)
        
        # Calculate overall scores
        vibe_match_overall = sum(v["vibe_match_score"] for v in venue_explanations) / len(venue_explanations)
        budget_fit_overall = ExplanationGenerator._calculate_overall_budget_fit(total_cost, budget_limit)
        flow_score = ExplanationGenerator._calculate_flow_score(venues)
        diversity_overall = sum(v["diversity_score"] for v in venue_explanations) / len(venue_explanations)
        
        summary = ExplanationGenerator._generate_summary(
            vibe_match_overall, budget_fit_overall, flow_score, diversity_overall, target_vibe
        )
        
        return {
            "total_fitness_score": ga_fitness_score,
            "vibe_match_score": vibe_match_overall,
            "budget_fit_score": budget_fit_overall,
            "flow_score": flow_score,
            "diversity_score": diversity_overall,
            "venue_explanations": venue_explanations,
            "summary": summary,
            "algorithm_used": algorithm_used,
            "constraints_applied": constraints or {}
        }
    
    @staticmethod
    def _calculate_vibe_match(venue: Dict[str, Any], target_vibe: str) -> float:
        """Calculate how well venue matches target vibe (0-100)"""
        venue_vibes = venue.get('vibes', [])
        venue_categories = venue.get('categories', [])
        
        # Direct vibe match
        if target_vibe in venue_vibes:
            return 95.0
        
        # Category-based match
        vibe_category_map = {
            "romantic": ["restaurant", "bar", "cafe", "park"],
            "adventurous": ["hiking", "sports", "outdoor", "activity"],
            "cozy": ["cafe", "bookstore", "library", "park"],
            "cultural": ["museum", "gallery", "theater", "historic"],
        }
        
        if target_vibe in vibe_category_map:
            matching_cats = [c for c in venue_categories if c in vibe_category_map[target_vibe]]
            if matching_cats:
                return 75.0 + len(matching_cats) * 5
        
        return 50.0  # Default
    
    @staticmethod
    def _calculate_budget_fit(venue: Dict[str, Any], budget_limit: float, index: int, total: int) -> float:
        """Calculate budget fit (0-100)"""
        price_tier = venue.get('price_tier', 2)
        estimated_cost = price_tier * 30
        
        # Allocate budget evenly across venues
        per_venue_budget = budget_limit / total
        
        if estimated_cost <= per_venue_budget:
            return 100.0
        elif estimated_cost <= per_venue_budget * 1.5:
            return 75.0
        else:
            return max(0, 50.0 - (estimated_cost - per_venue_budget) / 10)
    
    @staticmethod
    def _calculate_distance_score(venue: Dict[str, Any], index: int, venues: List[Dict]) -> float:
        """Calculate distance efficiency (0-100)"""
        if index == 0:
            return 100.0  # First venue is always good
        
        # Check if venue is reasonably close to previous
        prev_venue = venues[index - 1]
        lat1 = prev_venue.get('lat', 0)
        lon1 = prev_venue.get('lon', 0)
        lat2 = venue.get('lat', 0)
        lon2 = venue.get('lon', 0)
        
        # Simple distance calculation
        distance = math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) * 111  # km
        
        if distance < 2:
            return 100.0
        elif distance < 5:
            return 80.0
        elif distance < 10:
            return 60.0
        else:
            return 40.0
    
    @staticmethod
    def _calculate_rating_score(venue: Dict[str, Any]) -> float:
        """Calculate rating score (0-100)"""
        rating = venue.get('rating', 3.5)
        reviews = venue.get('reviews_count', 0)
        
        # Base score from rating
        score = (rating / 5.0) * 100
        
        # Boost for high review count
        if reviews > 100:
            score = min(100, score + 10)
        
        return score
    
    @staticmethod
    def _calculate_diversity_score(venue: Dict[str, Any], index: int, venues: List[Dict]) -> float:
        """Calculate diversity score (0-100)"""
        venue_type = venue.get('type', 'unknown')
        
        # Check if this type appears elsewhere
        type_count = sum(1 for v in venues if v.get('type') == venue_type)
        
        if type_count == 1:
            return 100.0  # Unique type
        elif type_count == 2:
            return 70.0
        else:
            return 40.0
    
    @staticmethod
    def _calculate_overall_budget_fit(total_cost: float, budget_limit: float) -> float:
        """Calculate overall budget fit (0-100)"""
        if total_cost <= budget_limit:
            return 100.0
        elif total_cost <= budget_limit * 1.2:
            return 80.0
        else:
            return max(0, 60.0 - (total_cost - budget_limit) / 10)
    
    @staticmethod
    def _calculate_flow_score(venues: List[Dict[str, Any]]) -> float:
        """Calculate logical date flow (0-100)"""
        # Check if venues follow logical sequence
        # Activity -> Meal -> Drinks -> Dessert
        
        type_sequence = [v.get('type', 'unknown') for v in venues]
        
        # Simple heuristic: variety is good
        unique_types = len(set(type_sequence))
        return min(100, (unique_types / len(venues)) * 100)
    
    @staticmethod
    def _generate_venue_explanation(
        venue: Dict[str, Any],
        vibe_match: float,
        budget_fit: float,
        distance_score: float,
        rating_score: float
    ) -> str:
        """Generate human-readable explanation for venue choice"""
        
        reasons = []
        
        if vibe_match > 80:
            reasons.append("perfect vibe match")
        elif vibe_match > 60:
            reasons.append("good vibe match")
        
        if rating_score > 85:
            reasons.append("highly rated")
        elif rating_score > 70:
            reasons.append("well-reviewed")
        
        if budget_fit > 90:
            reasons.append("great value")
        elif budget_fit > 70:
            reasons.append("reasonable price")
        
        if distance_score > 80:
            reasons.append("convenient location")
        
        reason_str = ", ".join(reasons) if reasons else "good choice"
        return f"{venue.get('name', 'This venue')} is a {reason_str}."
    
    @staticmethod
    def _generate_summary(
        vibe_match: float,
        budget_fit: float,
        flow_score: float,
        diversity_score: float,
        target_vibe: str
    ) -> str:
        """Generate summary explanation for entire plan"""
        
        parts = []
        
        if vibe_match > 80:
            parts.append(f"Perfect {target_vibe} evening")
        else:
            parts.append(f"Great {target_vibe} experience")
        
        if budget_fit > 90:
            parts.append("with excellent budget fit")
        elif budget_fit > 70:
            parts.append("within budget")
        
        if flow_score > 80:
            parts.append("and smooth flow")
        
        return " ".join(parts) + "."

