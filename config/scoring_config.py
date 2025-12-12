"""
Dynamic Scoring Configuration
Replaces hardcoded values with ML-learned and configurable parameters
"""

import logging
from typing import Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class ScoringConfig:
    """
    Centralized configuration for all scoring parameters.
    Values are learned from data or can be overridden.
    """
    
    # Vibe matching scores
    VIBE_MATCH_BONUS = 25  # Points for matching target vibe
    NEUTRAL_VIBE_BONUS = 5  # Points for neutral vibes
    
    # Rating/Review scoring
    BAYESIAN_AVERAGE_CONSTANT = 3.5  # Average rating across all venues
    BAYESIAN_MIN_REVIEWS = 10  # Minimum reviews to trust rating
    RATING_MULTIPLIER = 5  # Multiply rating by this for score
    
    # Hidden gem parameters
    HIDDEN_GEM_MIN_REVIEWS = 10
    HIDDEN_GEM_MAX_REVIEWS = 300
    HIDDEN_GEM_BONUS = 30
    HIDDEN_GEM_POPULARITY_PENALTY = 20  # Penalty if > 1000 reviews
    HIDDEN_GEM_RATING_MULTIPLIER = 5
    
    # Distance scoring
    DISTANCE_PENALTY_MULTIPLIER = 3  # Multiply distance^1.5 by this
    DISTANCE_EXPONENT = 1.5  # Exponential penalty for distance
    
    # Type matching scores
    TYPE_MATCH_BONUS = 500  # Big bonus for matching requested type
    WRONG_CUISINE_PENALTY = 800  # Harsh penalty for wrong cuisine
    COMPLEMENTARY_VENUE_BONUS = 20  # Bonus for diversity
    UNKNOWN_SLOT_PENALTY = 50  # Penalty for unknown slot
    REPEATED_TYPE_PENALTY = 100  # Penalty for repeating same type
    NEW_CATEGORY_BONUS = 15  # Bonus for trying something different
    
    # Randomness
    RANDOMNESS_MULTIPLIER = 3.0  # Max random bonus
    
    # Vibe-specific bonuses
    ROMANTIC_RESERVABLE_BONUS = 25
    ROMANTIC_KIDS_PENALTY = 30
    OUTDOOR_SEATING_BONUS = 40
    FAMILY_KIDS_BONUS = 50
    ENERGETIC_LIVE_MUSIC_BONUS = 40
    GROUP_FRIENDLY_BONUS = 40
    
    # GA parameters
    POPULATION_SIZE = 100
    GENERATIONS = 50
    MUTATION_RATE = 0.2
    CROSSOVER_RATE = 0.8
    ELITISM_COUNT = 5
    STAGNATION_LIMIT = 20
    
    # GA fitness scoring
    GA_INITIAL_SCORE = 1000
    GA_TYPE_COVERAGE_BONUS = 400
    GA_FULL_TYPE_COVERAGE_BONUS = 500
    GA_MISSING_TYPE_PENALTY = 300
    GA_DIVERSITY_BONUS = 50
    GA_GOOD_FLOW_BONUS = 100
    GA_RATING_MULTIPLIER = 10
    GA_DISTANCE_PENALTY = 5
    GA_VIBE_MATCH_BONUS = 30
    GA_LOCATION_MISMATCH_PENALTY = 50
    
    # Heuristic planner defaults
    DEFAULT_BUDGET = 150
    DEFAULT_DURATION_MINUTES = 180
    DEFAULT_ITINERARY_LENGTH = 3
    DEFAULT_VIBE = 'casual'
    
    # Budget tier mapping
    BUDGET_EXPENSIVE = 300
    BUDGET_CHEAP = 75
    
    # Duration mapping
    DURATION_QUICK = 60
    DURATION_ALL_DAY = 480
    
    @classmethod
    def learn_from_data(cls, venues_df) -> None:
        """
        Learn optimal parameters from venue data using statistical analysis.
        This should be called during initialization.
        """
        try:
            if venues_df.empty:
                logger.warning("Cannot learn from empty dataframe")
                return
            
            # Learn average rating
            avg_rating = venues_df['rating'].mean()
            if not np.isnan(avg_rating):
                cls.BAYESIAN_AVERAGE_CONSTANT = round(avg_rating, 2)
                logger.info(f"Learned average rating: {cls.BAYESIAN_AVERAGE_CONSTANT}")
            
            # Learn median reviews for hidden gems
            median_reviews = venues_df['reviews_count'].median()
            if not np.isnan(median_reviews):
                cls.HIDDEN_GEM_MAX_REVIEWS = int(median_reviews * 2)
                logger.info(f"Learned hidden gem max reviews: {cls.HIDDEN_GEM_MAX_REVIEWS}")
            
            # Learn budget distribution
            budget_75th = venues_df['cost'].quantile(0.75)
            if not np.isnan(budget_75th):
                cls.DEFAULT_BUDGET = int(budget_75th)
                logger.info(f"Learned default budget: {cls.DEFAULT_BUDGET}")
                
        except Exception as e:
            logger.warning(f"Could not learn from data: {e}")
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get all configuration as a dictionary"""
        return {k: v for k, v in cls.__dict__.items() 
                if not k.startswith('_') and not callable(v)}
    
    @classmethod
    def update_config(cls, **kwargs) -> None:
        """Update configuration values"""
        for key, value in kwargs.items():
            if hasattr(cls, key):
                setattr(cls, key, value)
                logger.info(f"Updated {key} = {value}")
            else:
                logger.warning(f"Unknown config key: {key}")

