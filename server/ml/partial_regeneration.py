"""
Partial Regeneration Service - Collaborative Date Planning

Allows users to:
- Regenerate one venue while keeping others
- Lock budget, time, or vibe constraints
- See why alternatives were rejected

Makes the app feel collaborative instead of "one-shot AI".
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import copy

logger = logging.getLogger(__name__)


class PartialRegenerationService:
    """Service for regenerating parts of date plans"""
    
    @staticmethod
    def regenerate_venue(
        current_plan: List[Dict[str, Any]],
        venue_index: int,
        locked_constraints: Dict[str, Any],
        available_venues: List[Dict[str, Any]],
        ga_planner_func=None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Regenerate a single venue while keeping others locked.
        
        Args:
            current_plan: Current itinerary
            venue_index: Index of venue to regenerate
            locked_constraints: Constraints to maintain
            available_venues: Pool of venues to choose from
            ga_planner_func: Function to run GA planning
            
        Returns:
            Tuple of (new_plan, explanation)
        """
        
        if venue_index < 0 or venue_index >= len(current_plan):
            raise ValueError(f"Invalid venue index: {venue_index}")
        
        # Extract locked constraints
        locked_budget = locked_constraints.get("lock_budget", False)
        locked_vibe = locked_constraints.get("lock_vibe", False)
        locked_duration = locked_constraints.get("lock_duration", False)
        
        # Calculate remaining budget for this venue
        total_budget = locked_constraints.get("total_budget", 150)
        current_cost = sum(v.get("price_tier", 1) * 30 for v in current_plan)
        remaining_budget = total_budget - current_cost + (current_plan[venue_index].get("price_tier", 1) * 30)
        
        # Build constraints for regeneration
        regen_constraints = {
            "vibe": locked_constraints.get("vibe") if locked_vibe else None,
            "budget": remaining_budget if locked_budget else None,
            "duration": locked_constraints.get("duration") if locked_duration else None,
            "exclude_ids": [v.get("id") for v in current_plan if current_plan.index(v) != venue_index],
            "venue_index": venue_index,
            "total_venues": len(current_plan)
        }
        
        # Find alternative venues
        alternatives = PartialRegenerationService._find_alternatives(
            current_plan[venue_index],
            available_venues,
            regen_constraints
        )
        
        if not alternatives:
            logger.warning(f"No alternatives found for venue {venue_index}")
            return current_plan, {"error": "No suitable alternatives found"}
        
        # Select best alternative
        best_alternative = alternatives[0]
        
        # Create new plan with regenerated venue
        new_plan = copy.deepcopy(current_plan)
        new_plan[venue_index] = best_alternative
        
        # Generate explanation
        explanation = {
            "regenerated_venue_index": venue_index,
            "old_venue": current_plan[venue_index].get("name"),
            "new_venue": best_alternative.get("name"),
            "reason": f"Better match for {regen_constraints.get('vibe', 'your preferences')}",
            "alternatives_considered": len(alternatives),
            "alternatives": [
                {
                    "name": alt.get("name"),
                    "reason": PartialRegenerationService._explain_alternative(alt, current_plan[venue_index])
                }
                for alt in alternatives[:3]
            ],
            "locked_constraints": locked_constraints
        }
        
        return new_plan, explanation
    
    @staticmethod
    def _find_alternatives(
        current_venue: Dict[str, Any],
        available_venues: List[Dict[str, Any]],
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find alternative venues matching constraints"""
        
        alternatives = []
        exclude_ids = constraints.get("exclude_ids", [])
        target_vibe = constraints.get("vibe")
        budget = constraints.get("budget")
        
        for venue in available_venues:
            # Skip excluded venues
            if venue.get("id") in exclude_ids:
                continue
            
            # Skip current venue
            if venue.get("id") == current_venue.get("id"):
                continue
            
            # Check vibe match
            if target_vibe:
                venue_vibes = venue.get("vibes", [])
                if target_vibe not in venue_vibes:
                    continue
            
            # Check budget
            if budget:
                venue_cost = venue.get("price_tier", 1) * 30
                if venue_cost > budget * 1.2:  # Allow 20% overage
                    continue
            
            # Calculate score
            score = PartialRegenerationService._score_alternative(venue, current_venue, target_vibe)
            alternatives.append((score, venue))
        
        # Sort by score and return venues
        alternatives.sort(key=lambda x: x[0], reverse=True)
        return [v for _, v in alternatives[:10]]
    
    @staticmethod
    def _score_alternative(
        venue: Dict[str, Any],
        current_venue: Dict[str, Any],
        target_vibe: Optional[str]
    ) -> float:
        """Score how good an alternative is"""
        
        score = 0.0
        
        # Rating bonus
        rating = venue.get("rating", 3.5)
        score += rating * 10
        
        # Review count bonus
        reviews = venue.get("reviews_count", 0)
        if reviews > 100:
            score += 20
        elif reviews > 50:
            score += 10
        
        # Vibe match bonus
        if target_vibe and target_vibe in venue.get("vibes", []):
            score += 30
        
        # Diversity bonus (different type than current)
        if venue.get("type") != current_venue.get("type"):
            score += 15
        
        return score
    
    @staticmethod
    def _explain_alternative(
        alternative: Dict[str, Any],
        current_venue: Dict[str, Any]
    ) -> str:
        """Generate explanation for why alternative was considered"""
        
        reasons = []
        
        # Rating comparison
        alt_rating = alternative.get("rating", 0)
        curr_rating = current_venue.get("rating", 0)
        if alt_rating > curr_rating:
            reasons.append(f"higher rated ({alt_rating:.1f} vs {curr_rating:.1f})")
        
        # Type difference
        if alternative.get("type") != current_venue.get("type"):
            reasons.append(f"different type ({alternative.get('type')})")
        
        # Review count
        alt_reviews = alternative.get("reviews_count", 0)
        if alt_reviews > 100:
            reasons.append("well-reviewed")
        
        if not reasons:
            reasons.append("good alternative")
        
        return ", ".join(reasons)
    
    @staticmethod
    def lock_constraints(
        plan: List[Dict[str, Any]],
        lock_budget: bool = False,
        lock_vibe: bool = False,
        lock_duration: bool = False,
        vibe: Optional[str] = None,
        budget: Optional[float] = None,
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create locked constraints for partial regeneration.
        
        Returns dict that can be passed to regenerate_venue()
        """
        
        total_cost = sum(v.get("price_tier", 1) * 30 for v in plan)
        total_duration = sum(v.get("duration_min", 60) for v in plan)
        
        return {
            "lock_budget": lock_budget,
            "lock_vibe": lock_vibe,
            "lock_duration": lock_duration,
            "vibe": vibe,
            "budget": budget or 150,
            "duration": duration or total_duration,
            "total_budget": budget or 150,
            "original_plan_cost": total_cost,
            "original_plan_duration": total_duration
        }

