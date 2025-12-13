"""
Feature Learning - Learn which features matter most for each vibe
Replaces hard-coded feature bonuses
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Learned feature importance per vibe
_feature_importance = {
    'romantic': {},
    'energetic': {},
    'cozy': {},
    'fancy': {},
    'casual': {},
    'hipster': {},
    'historic': {},
    'outdoors': {},
    'artsy': {},
    'family': {},
    'foodie': {},
    'scenic': {},
    'wellness': {}
}

def learn_vibe_feature_importance(interactions_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    Learn which features matter most for each vibe from user feedback
    
    Args:
        interactions_df: DataFrame with columns:
            - vibe: Venue vibe
            - feature: Feature name (e.g., 'reservable', 'outdoor_seating')
            - accepted: Boolean, whether user accepted
    
    Returns:
        Dictionary mapping vibe -> feature -> importance score
    """
    global _feature_importance
    
    try:
        if len(interactions_df) == 0:
            logger.warning("No interaction data, using defaults")
            return _feature_importance
        
        # For each vibe, calculate feature importance
        for vibe in _feature_importance.keys():
            vibe_data = interactions_df[interactions_df['vibe'] == vibe]
            
            if len(vibe_data) == 0:
                continue
            
            # Calculate acceptance rate for each feature
            feature_importance = {}
            for feature in vibe_data['feature'].unique():
                feature_data = vibe_data[vibe_data['feature'] == feature]
                acceptance_rate = feature_data['accepted'].mean()
                
                # Importance = how much this feature increases acceptance
                feature_importance[feature] = float(acceptance_rate)
            
            _feature_importance[vibe] = feature_importance
        
        logger.info(f"Learned feature importance for {len(_feature_importance)} vibes")
        return _feature_importance
    except Exception as e:
        logger.error(f"Error learning feature importance: {e}")
        return _feature_importance

def get_feature_bonus(vibe: str, feature: str, default_bonus: float = 25.0) -> float:
    """
    Get bonus score for a feature in a specific vibe
    
    Args:
        vibe: Venue vibe
        feature: Feature name
        default_bonus: Default bonus if not learned
    
    Returns:
        Bonus score
    """
    if vibe in _feature_importance and feature in _feature_importance[vibe]:
        # Scale learned importance to bonus range (0-100)
        importance = _feature_importance[vibe][feature]
        return float(importance * 100)
    return default_bonus

def get_feature_penalty(vibe: str, feature: str, default_penalty: float = 25.0) -> float:
    """
    Get penalty score for a missing feature in a specific vibe
    
    Args:
        vibe: Venue vibe
        feature: Feature name
        default_penalty: Default penalty if not learned
    
    Returns:
        Penalty score
    """
    if vibe in _feature_importance and feature in _feature_importance[vibe]:
        # Penalty = inverse of importance
        importance = _feature_importance[vibe][feature]
        return float((1.0 - importance) * 100)
    return default_penalty

def get_vibe_features(vibe: str) -> Dict[str, float]:
    """
    Get all learned features for a vibe
    
    Args:
        vibe: Venue vibe
    
    Returns:
        Dictionary mapping feature -> importance
    """
    return _feature_importance.get(vibe, {}).copy()

def get_top_features(vibe: str, top_n: int = 5) -> List[tuple]:
    """
    Get top N features for a vibe
    
    Args:
        vibe: Venue vibe
        top_n: Number of top features to return
    
    Returns:
        List of (feature, importance) tuples, sorted by importance
    """
    features = _feature_importance.get(vibe, {})
    sorted_features = sorted(features.items(), key=lambda x: x[1], reverse=True)
    return sorted_features[:top_n]

def get_learned_importance() -> Dict[str, Dict[str, float]]:
    """Get all learned feature importance"""
    return {k: v.copy() for k, v in _feature_importance.items()}

def reset_importance():
    """Reset to default (empty) feature importance"""
    global _feature_importance
    _feature_importance = {
        'romantic': {},
        'energetic': {},
        'cozy': {},
        'fancy': {},
        'casual': {},
        'hipster': {},
        'historic': {},
        'outdoors': {},
        'artsy': {},
        'family': {},
        'foodie': {},
        'scenic': {},
        'wellness': {}
    }

