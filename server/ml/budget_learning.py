"""
Budget Tier Learning - Learn budget tiers from actual price distribution
Replaces hard-coded budget ranges
"""

import pandas as pd
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Learned budget tiers (will be populated from data)
_learned_tiers = {
    1: (0, 50),      # Budget
    2: (50, 150),    # Moderate
    3: (150, 500)    # Expensive
}

def learn_budget_tiers(venues_df: pd.DataFrame) -> Dict[int, Tuple[float, float]]:
    """
    Learn budget tiers from actual venue price distribution
    
    Args:
        venues_df: DataFrame with 'cost' column
    
    Returns:
        Dictionary mapping tier (1-3) to (min, max) price range
    """
    global _learned_tiers
    
    try:
        prices = venues_df['cost'].dropna()
        
        if len(prices) == 0:
            logger.warning("No price data available, using defaults")
            return _learned_tiers
        
        # Learn quartiles from data
        q33 = prices.quantile(0.33)
        q67 = prices.quantile(0.67)
        
        _learned_tiers = {
            1: (float(prices.min()), float(q33)),
            2: (float(q33), float(q67)),
            3: (float(q67), float(prices.max()))
        }
        
        logger.info(f"Learned budget tiers: {_learned_tiers}")
        return _learned_tiers
    except Exception as e:
        logger.error(f"Error learning budget tiers: {e}")
        return _learned_tiers

def get_budget_tier(price: float) -> int:
    """
    Get budget tier for a given price
    
    Args:
        price: Venue price
    
    Returns:
        Tier number (1, 2, or 3)
    """
    if price <= _learned_tiers[1][1]:
        return 1
    elif price <= _learned_tiers[2][1]:
        return 2
    else:
        return 3

def get_tier_range(tier: int) -> Tuple[float, float]:
    """
    Get price range for a budget tier
    
    Args:
        tier: Tier number (1, 2, or 3)
    
    Returns:
        (min_price, max_price) tuple
    """
    return _learned_tiers.get(tier, (0, 500))

def is_within_budget(price: float, budget: float, tolerance: float = 0.1) -> bool:
    """
    Check if price is within budget (with tolerance)
    
    Args:
        price: Venue price
        budget: User budget
        tolerance: Tolerance percentage (0.1 = 10% over)
    
    Returns:
        True if price is within budget + tolerance
    """
    return price <= budget * (1 + tolerance)

def get_budget_score(price: float, budget: float) -> float:
    """
    Get budget score for a venue (0-1)
    
    Args:
        price: Venue price
        budget: User budget
    
    Returns:
        Score (1.0 = perfect, 0.0 = way over budget)
    """
    if price <= budget:
        return 1.0
    else:
        # Penalize based on how much over budget
        overage = (price - budget) / budget
        return max(0.0, 1.0 - overage)

def get_learned_tiers() -> Dict[int, Tuple[float, float]]:
    """Get current learned budget tiers"""
    return _learned_tiers.copy()

def reset_tiers():
    """Reset to default budget tiers"""
    global _learned_tiers
    _learned_tiers = {
        1: (0, 50),
        2: (50, 150),
        3: (150, 500)
    }

