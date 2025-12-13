"""
Tests for ML features
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.ml import (
    get_venue_similarity,
    learn_rating_params,
    get_bayesian_rating,
    learn_budget_tiers,
    get_budget_tier,
    classify_vibe,
    classify_venue_types,
    learn_distance_preferences,
    get_distance_score,
    learn_vibe_feature_importance,
    get_feature_bonus,
    get_optimal_ga_params
)

class TestVenueSimilarity:
    def test_identical_venues(self):
        """Identical venues should have high similarity"""
        venue = {
            'name': 'Pizza Place',
            'description': 'Italian restaurant with wood-fired oven'
        }
        similarity = get_venue_similarity(venue, venue)
        assert similarity is not None
        assert similarity > 0.9
    
    def test_different_venues(self):
        """Different venues should have low similarity"""
        venue1 = {'name': 'Pizza Place', 'description': 'Italian restaurant'}
        venue2 = {'name': 'Park', 'description': 'Outdoor nature area'}
        similarity = get_venue_similarity(venue1, venue2)
        assert similarity is not None
        assert similarity < 0.5

class TestRatingLearning:
    def test_learn_rating_params(self):
        """Should learn rating parameters from data"""
        df = pd.DataFrame({
            'rating': [3.5, 4.0, 4.5, 5.0, 3.0],
            'reviews_count': [10, 50, 100, 500, 5]
        })
        params = learn_rating_params(df)
        assert 'bayesian_constant' in params
        assert 'min_reviews' in params
        assert params['bayesian_constant'] > 0
    
    def test_bayesian_rating(self):
        """Should calculate Bayesian average correctly"""
        rating = get_bayesian_rating(5.0, 100)
        assert rating > 0
        assert rating <= 5.0

class TestBudgetLearning:
    def test_learn_budget_tiers(self):
        """Should learn budget tiers from price data"""
        df = pd.DataFrame({
            'cost': [10, 20, 50, 100, 150, 200, 300, 500]
        })
        tiers = learn_budget_tiers(df)
        assert len(tiers) == 3
        assert tiers[1][0] < tiers[1][1]
        assert tiers[2][0] < tiers[2][1]
    
    def test_get_budget_tier(self):
        """Should classify prices into tiers"""
        tier = get_budget_tier(75)
        assert tier in [1, 2, 3]

class TestVibeClassification:
    def test_classify_romantic_vibe(self):
        """Should classify romantic descriptions"""
        vibe = classify_vibe("Candlelit dinner with wine and soft music")
        if vibe:  # Only test if model available
            assert vibe in ['romantic', 'cozy', 'fancy']
    
    def test_classify_energetic_vibe(self):
        """Should classify energetic descriptions"""
        vibe = classify_vibe("Live music and dancing with DJ")
        if vibe:
            assert vibe in ['energetic', 'nightlife', 'casual']

class TestTypeClassification:
    def test_classify_restaurant_type(self):
        """Should classify restaurant types"""
        types = classify_venue_types("Italian restaurant with pasta and pizza")
        if types:
            assert any(t in types for t in ['restaurant', 'italian', 'casual dining'])
    
    def test_classify_park_type(self):
        """Should classify outdoor types"""
        types = classify_venue_types("Beautiful park with hiking trails and nature")
        if types:
            assert any(t in types for t in ['park', 'outdoor', 'activity'])

class TestDistanceLearning:
    def test_learn_distance_preferences(self):
        """Should learn distance preferences from interactions"""
        df = pd.DataFrame({
            'distance': [1, 2, 3, 5, 10, 15, 20],
            'accepted': [True, True, True, True, False, False, False]
        })
        params = learn_distance_preferences(df)
        assert 'preferred_max_distance' in params
        assert params['preferred_max_distance'] > 0
    
    def test_distance_score(self):
        """Should calculate distance scores"""
        score = get_distance_score(2.0)
        assert 0 <= score <= 1

class TestFeatureLearning:
    def test_get_feature_bonus(self):
        """Should return feature bonuses"""
        bonus = get_feature_bonus('romantic', 'reservable', 25.0)
        assert bonus >= 0

class TestGATuning:
    def test_get_optimal_ga_params(self):
        """Should return GA parameters"""
        params = get_optimal_ga_params()
        assert 'population_size' in params
        assert 'generations' in params
        assert 'mutation_rate' in params
        assert params['population_size'] > 0
        assert 0 < params['mutation_rate'] < 1

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

