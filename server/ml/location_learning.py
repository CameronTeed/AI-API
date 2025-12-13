"""
Location Relevance Learning - Learn distance preferences from user behavior
Replaces hard-coded distance penalties
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Learned distance preferences
_distance_params = {
    'preferred_max_distance': 5.0,  # km
    'acceptable_max_distance': 15.0,  # km
    'distance_penalty_multiplier': 1.0,
    'distance_decay_rate': 0.1
}

def learn_distance_preferences(interactions_df: pd.DataFrame) -> Dict[str, float]:
    """
    Learn distance preferences from user interaction data
    
    Args:
        interactions_df: DataFrame with columns:
            - distance: Distance in km
            - accepted: Boolean, whether user accepted the venue
    
    Returns:
        Dictionary with learned distance parameters
    """
    global _distance_params
    
    try:
        if len(interactions_df) == 0:
            logger.warning("No interaction data, using defaults")
            return _distance_params
        
        # Find distance where acceptance rate drops significantly
        accepted = interactions_df[interactions_df['accepted'] == True]
        rejected = interactions_df[interactions_df['accepted'] == False]
        
        if len(accepted) > 0:
            preferred_max = accepted['distance'].quantile(0.75)
        else:
            preferred_max = 5.0
        
        if len(rejected) > 0:
            acceptable_max = rejected['distance'].quantile(0.25)
        else:
            acceptable_max = 15.0
        
        # Ensure reasonable bounds
        preferred_max = max(1.0, min(preferred_max, 10.0))
        acceptable_max = max(preferred_max, min(acceptable_max, 30.0))
        
        _distance_params = {
            'preferred_max_distance': float(preferred_max),
            'acceptable_max_distance': float(acceptable_max),
            'distance_penalty_multiplier': 1.0,
            'distance_decay_rate': 0.1
        }
        
        logger.info(f"Learned distance preferences: {_distance_params}")
        return _distance_params
    except Exception as e:
        logger.error(f"Error learning distance preferences: {e}")
        return _distance_params

def get_distance_score(distance: float) -> float:
    """
    Get distance score (0-1) based on learned preferences
    
    Args:
        distance: Distance in km
    
    Returns:
        Score (1.0 = preferred, 0.0 = too far)
    """
    preferred = _distance_params['preferred_max_distance']
    acceptable = _distance_params['acceptable_max_distance']
    decay = _distance_params['distance_decay_rate']
    
    if distance <= preferred:
        return 1.0
    elif distance <= acceptable:
        # Linear decay from preferred to acceptable
        ratio = (distance - preferred) / (acceptable - preferred)
        return 1.0 - (ratio * 0.5)
    else:
        # Exponential decay beyond acceptable
        excess = distance - acceptable
        return max(0.0, 0.5 * np.exp(-decay * excess))

def get_distance_penalty(distance: float) -> float:
    """
    Get distance penalty (0-1) for scoring
    
    Args:
        distance: Distance in km
    
    Returns:
        Penalty (0 = no penalty, 1 = maximum penalty)
    """
    return 1.0 - get_distance_score(distance)

def is_within_preferred_distance(distance: float) -> bool:
    """Check if distance is within preferred range"""
    return distance <= _distance_params['preferred_max_distance']

def is_within_acceptable_distance(distance: float) -> bool:
    """Check if distance is within acceptable range"""
    return distance <= _distance_params['acceptable_max_distance']

def get_learned_params() -> Dict[str, float]:
    """Get current learned distance parameters"""
    return _distance_params.copy()

def reset_params():
    """Reset to default distance parameters"""
    global _distance_params
    _distance_params = {
        'preferred_max_distance': 5.0,
        'acceptable_max_distance': 15.0,
        'distance_penalty_multiplier': 1.0,
        'distance_decay_rate': 0.1
    }

