"""
Tests for Phase 1: Smart Question Routing Implementation

Tests the question classifier and venue data fetcher
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from server.ml.question_classifier import QuestionClassifier
from server.tools.venue_data_fetcher import VenueDataFetcher


class TestQuestionClassifier:
    """Test question type classification"""

    def test_dietary_question(self):
        """Test dietary question detection"""
        q_type, source, desc = QuestionClassifier.classify("Do they have vegetarian options?")
        assert q_type == "dietary"
        assert source == "database"
        assert "Dietary" in desc

    def test_hours_question(self):
        """Test hours question detection"""
        q_type, source, desc = QuestionClassifier.classify("What are the hours?")
        assert q_type == "hours"
        assert source == "google_places"

    def test_accessibility_question(self):
        """Test accessibility question detection"""
        q_type, source, desc = QuestionClassifier.classify("Is it wheelchair accessible?")
        assert q_type == "accessibility"
        assert source == "database"

    def test_parking_question(self):
        """Test parking question detection"""
        q_type, source, desc = QuestionClassifier.classify("Is there parking?")
        assert q_type == "parking"
        assert source == "database"

    def test_phone_question(self):
        """Test phone question detection"""
        q_type, source, desc = QuestionClassifier.classify("What's their phone number?")
        assert q_type == "phone"
        assert source == "google_places"

    def test_website_question(self):
        """Test website question detection"""
        q_type, source, desc = QuestionClassifier.classify("Can I book online?")
        assert q_type == "website"
        assert source == "google_places"

    def test_reviews_question(self):
        """Test reviews question detection"""
        q_type, source, desc = QuestionClassifier.classify("What do people say about it?")
        assert q_type == "reviews"
        assert source == "web_search"

    def test_price_question(self):
        """Test price question detection"""
        q_type, source, desc = QuestionClassifier.classify("How much does it cost?")
        assert q_type == "price"
        assert source == "database"

    def test_kids_question(self):
        """Test kids question detection"""
        q_type, source, desc = QuestionClassifier.classify("Is it good for kids?")
        assert q_type == "kids"
        assert source == "database"

    def test_dogs_question(self):
        """Test dogs question detection"""
        q_type, source, desc = QuestionClassifier.classify("Can we bring our dog?")
        assert q_type == "dogs"
        assert source == "database"

    def test_menu_question(self):
        """Test menu question detection"""
        q_type, source, desc = QuestionClassifier.classify("What kind of food do they serve?")
        assert q_type == "menu"
        assert source == "web_search"

    def test_atmosphere_question(self):
        """Test atmosphere question detection"""
        q_type, source, desc = QuestionClassifier.classify("Is it romantic?")
        assert q_type == "atmosphere"
        assert source == "web_search"

    def test_unknown_question(self):
        """Test unknown question defaults to web search"""
        q_type, source, desc = QuestionClassifier.classify("Something random?")
        assert q_type == "general"
        assert source == "web_search"

    def test_get_all_types(self):
        """Test getting all question types"""
        types = QuestionClassifier.get_all_types()
        assert "dietary" in types
        assert "hours" in types
        assert "accessibility" in types
        assert len(types) > 0


class TestVenueDataFetcher:
    """Test venue data fetcher"""

    def test_fetcher_initialization(self):
        """Test fetcher can be initialized without DB"""
        fetcher = VenueDataFetcher(None)
        assert fetcher is not None

    def test_empty_venue_ids(self):
        """Test handling of empty venue IDs"""
        fetcher = VenueDataFetcher(None)
        result = fetcher.fetch_venue_details([], "dietary", "test")
        assert result == []

    def test_format_venue_details_empty(self):
        """Test formatting empty venue details"""
        fetcher = VenueDataFetcher(None)
        result = fetcher.format_venue_details([], "dietary")
        assert "No venue details available" in result

    def test_format_venue_details_dietary(self):
        """Test formatting dietary venue details"""
        fetcher = VenueDataFetcher(None)
        venues = [
            {
                "name": "Restaurant A",
                "address": "123 Main St",
                "serves_vegetarian": True
            }
        ]
        result = fetcher.format_venue_details(venues, "dietary")
        assert "Restaurant A" in result
        assert "123 Main St" in result
        assert "Vegetarian" in result

    def test_format_venue_details_price(self):
        """Test formatting price venue details"""
        fetcher = VenueDataFetcher(None)
        venues = [
            {
                "name": "Restaurant B",
                "address": "456 Oak Ave",
                "cost": 50,
                "price_level": "$$"
            }
        ]
        result = fetcher.format_venue_details(venues, "price")
        assert "Restaurant B" in result
        assert "50" in result
        assert "$$" in result

    def test_format_venue_details_reviews(self):
        """Test formatting review venue details"""
        fetcher = VenueDataFetcher(None)
        venues = [
            {
                "name": "Restaurant C",
                "address": "789 Pine Rd",
                "rating": 4.5,
                "reviews_count": 100,
                "review_summary": "Great food!"
            }
        ]
        result = fetcher.format_venue_details(venues, "reviews")
        assert "Restaurant C" in result
        assert "4.5" in result
        assert "100" in result
        assert "Great food!" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

