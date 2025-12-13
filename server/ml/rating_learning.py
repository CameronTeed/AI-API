"""
Rating Interpretation - Learn rating parameters from actual data
Replaces hard-coded Bayesian average constants
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Learned parameters (will be populated from data)
_learned_params = {
    'bayesian_constant': 3.5,  # Default fallback
    'min_reviews': 10,
    'rating_std': 0.8,
    'median_reviews': 50,
    'rating_mean': 4.0
}

def learn_rating_params(venues_df: pd.DataFrame) -> Dict[str, float]:
    """
    Learn rating parameters from actual venue data
    
    Args:
        venues_df: DataFrame with 'rating' and 'reviews_count' columns
    
    Returns:
        Dictionary with learned parameters
    """
    global _learned_params
    
    try:
        ratings = venues_df['rating'].dropna()
        reviews = venues_df['reviews_count'].dropna()
        
        if len(ratings) == 0 or len(reviews) == 0:
            logger.warning("No rating data available, using defaults")
            return _learned_params
        
        _learned_params = {
            'bayesian_constant': float(ratings.mean()),
            'min_reviews': int(reviews.quantile(0.25)),
            'rating_std': float(ratings.std()),
            'median_reviews': int(reviews.median()),
            'rating_mean': float(ratings.mean())
        }
        
        logger.info(f"Learned rating params: {_learned_params}")
        return _learned_params
    except Exception as e:
        logger.error(f"Error learning rating params: {e}")
        return _learned_params

def get_bayesian_rating(rating: float, reviews_count: int) -> float:
    """
    Calculate Bayesian average rating
    Formula: (R * v + C * m) / (v + m)
    where R = actual rating, v = reviews, C = average rating, m = min reviews
    
    Args:
        rating: Actual venue rating
        reviews_count: Number of reviews
    
    Returns:
        Bayesian average rating
    """
    C = _learned_params['bayesian_constant']
    m = _learned_params['min_reviews']
    
    if pd.isna(rating) or pd.isna(reviews_count):
        return C
    
    bayesian = (rating * reviews_count + C * m) / (reviews_count + m)
    return float(bayesian)

def get_rating_confidence(reviews_count: int) -> float:
    """
    Get confidence score for a rating based on review count
    
    Args:
        reviews_count: Number of reviews
    
    Returns:
        Confidence score (0-1)
    """
    min_reviews = _learned_params['min_reviews']
    median_reviews = _learned_params['median_reviews']
    
    if reviews_count < min_reviews:
        return float(reviews_count / min_reviews)
    elif reviews_count < median_reviews:
        return float(0.5 + (reviews_count - min_reviews) / (median_reviews - min_reviews) * 0.5)
    else:
        return 1.0

def is_hidden_gem(rating: float, reviews_count: int) -> bool:
    """
    Determine if a venue is a hidden gem
    (Good rating with few reviews)
    
    Args:
        rating: Venue rating
        reviews_count: Number of reviews
    
    Returns:
        True if venue is a hidden gem
    """
    min_reviews = _learned_params['min_reviews']
    median_reviews = _learned_params['median_reviews']
    rating_mean = _learned_params['rating_mean']
    
    # Hidden gem: good rating, but fewer reviews than median
    return (rating >= rating_mean and 
            min_reviews <= reviews_count <= median_reviews)

def get_learned_params() -> Dict[str, float]:
    """Get current learned parameters"""
    return _learned_params.copy()

def reset_params():
    """Reset to default parameters"""
    global _learned_params
    _learned_params = {
        'bayesian_constant': 3.5,
        'min_reviews': 10,
        'rating_std': 0.8,
        'median_reviews': 50,
        'rating_mean': 4.0
    }

