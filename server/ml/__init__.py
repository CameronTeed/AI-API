"""
ML Features Module - Pre-trained models and data-driven learning
"""

from .venue_similarity import get_venue_similarity, get_venue_embeddings
from .rating_learning import learn_rating_params, get_bayesian_rating
from .budget_learning import learn_budget_tiers, get_budget_tier
from .vibe_classifier import classify_vibe, classify_vibe_batch
from .type_classifier import classify_venue_types, classify_venue_types_batch
from .location_learning import learn_distance_preferences, get_distance_score
from .feature_learning import learn_vibe_feature_importance, get_feature_bonus
from .ga_tuning import optimize_ga_parameters, get_optimal_ga_params

__all__ = [
    # Venue Similarity
    'get_venue_similarity',
    'get_venue_embeddings',
    
    # Rating Learning
    'learn_rating_params',
    'get_bayesian_rating',
    
    # Budget Learning
    'learn_budget_tiers',
    'get_budget_tier',
    
    # Vibe Classification
    'classify_vibe',
    'classify_vibe_batch',
    
    # Type Classification
    'classify_venue_types',
    'classify_venue_types_batch',
    
    # Location Learning
    'learn_distance_preferences',
    'get_distance_score',
    
    # Feature Learning
    'learn_vibe_feature_importance',
    'get_feature_bonus',
    
    # GA Tuning
    'optimize_ga_parameters',
    'get_optimal_ga_params',
]

