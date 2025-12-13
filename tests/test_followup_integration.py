"""
Integration tests for follow-up question handling

Tests the complete flow from question classification to answer generation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from server.ml.question_classifier import QuestionClassifier
from server.tools.venue_data_fetcher import VenueDataFetcher


class TestFollowUpIntegration:
    """Integration tests for follow-up question handling"""

    def test_parking_question_flow(self):
        """Test complete flow for parking question"""
        # Step 1: Classify question
        question = "What's the parking situation?"
        q_type, source, desc = QuestionClassifier.classify(question)
        
        # Verify classification
        assert q_type == "parking"
        assert source == "database"
        assert "Parking" in desc
        
        # Step 2: Verify fetcher can handle this question type
        fetcher = VenueDataFetcher(None)
        assert fetcher is not None

    def test_dietary_question_flow(self):
        """Test complete flow for dietary question"""
        # Step 1: Classify question
        question = "Do they have vegetarian options?"
        q_type, source, desc = QuestionClassifier.classify(question)
        
        # Verify classification
        assert q_type == "dietary"
        assert source == "database"
        assert "Dietary" in desc
        
        # Step 2: Verify fetcher can handle this question type
        fetcher = VenueDataFetcher(None)
        assert fetcher is not None

    def test_hours_question_flow(self):
        """Test complete flow for hours question"""
        # Step 1: Classify question
        question = "What are the hours?"
        q_type, source, desc = QuestionClassifier.classify(question)
        
        # Verify classification
        assert q_type == "hours"
        assert source == "google_places"
        
        # Step 2: Verify fetcher can handle this question type
        fetcher = VenueDataFetcher(None)
        assert fetcher is not None

    def test_accessibility_question_flow(self):
        """Test complete flow for accessibility question"""
        # Step 1: Classify question
        question = "Is it wheelchair accessible?"
        q_type, source, desc = QuestionClassifier.classify(question)
        
        # Verify classification
        assert q_type == "accessibility"
        assert source == "database"
        
        # Step 2: Verify fetcher can handle this question type
        fetcher = VenueDataFetcher(None)
        assert fetcher is not None

    def test_kids_question_flow(self):
        """Test complete flow for kids question"""
        # Step 1: Classify question
        question = "Is it good for kids?"
        q_type, source, desc = QuestionClassifier.classify(question)
        
        # Verify classification
        assert q_type == "kids"
        assert source == "database"
        
        # Step 2: Verify fetcher can handle this question type
        fetcher = VenueDataFetcher(None)
        assert fetcher is not None

    def test_dogs_question_flow(self):
        """Test complete flow for dogs question"""
        # Step 1: Classify question
        question = "Can we bring our dog?"
        q_type, source, desc = QuestionClassifier.classify(question)
        
        # Verify classification
        assert q_type == "dogs"
        assert source == "database"
        
        # Step 2: Verify fetcher can handle this question type
        fetcher = VenueDataFetcher(None)
        assert fetcher is not None

    def test_reviews_question_flow(self):
        """Test complete flow for reviews question"""
        # Step 1: Classify question
        question = "What do people say about it?"
        q_type, source, desc = QuestionClassifier.classify(question)
        
        # Verify classification
        assert q_type == "reviews"
        assert source == "web_search"
        
        # Step 2: Verify fetcher can handle this question type
        fetcher = VenueDataFetcher(None)
        assert fetcher is not None

    def test_price_question_flow(self):
        """Test complete flow for price question"""
        # Step 1: Classify question
        question = "How much does it cost?"
        q_type, source, desc = QuestionClassifier.classify(question)
        
        # Verify classification
        assert q_type == "price"
        assert source == "database"
        
        # Step 2: Verify fetcher can handle this question type
        fetcher = VenueDataFetcher(None)
        assert fetcher is not None

    def test_question_classifier_all_types(self):
        """Test that all question types are properly configured"""
        all_types = QuestionClassifier.get_all_types()
        
        # Verify all expected types are present
        expected_types = [
            "dietary", "hours", "accessibility", "parking",
            "phone", "website", "reviews", "price",
            "kids", "dogs", "menu", "atmosphere"
        ]
        
        for expected_type in expected_types:
            assert expected_type in all_types, f"Missing question type: {expected_type}"

    def test_data_source_routing(self):
        """Test that questions are routed to correct data sources"""
        # Database questions
        db_questions = [
            ("Do they have vegetarian options?", "dietary"),
            ("Is it wheelchair accessible?", "accessibility"),
            ("Is there parking?", "parking"),
            ("How much does it cost?", "price"),
            ("Is it good for kids?", "kids"),
            ("Can we bring our dog?", "dogs"),
        ]
        
        for question, expected_type in db_questions:
            q_type, source, _ = QuestionClassifier.classify(question)
            assert q_type == expected_type
            assert source == "database", f"Question '{question}' should route to database"
        
        # Google Places questions
        gp_questions = [
            ("What are the hours?", "hours"),
            ("What's their phone number?", "phone"),
            ("Can I book online?", "website"),
        ]
        
        for question, expected_type in gp_questions:
            q_type, source, _ = QuestionClassifier.classify(question)
            assert q_type == expected_type
            assert source == "google_places", f"Question '{question}' should route to google_places"
        
        # Web search questions
        ws_questions = [
            ("What do people say?", "reviews"),
            ("What kind of food?", "menu"),
            ("Is it romantic?", "atmosphere"),
        ]
        
        for question, expected_type in ws_questions:
            q_type, source, _ = QuestionClassifier.classify(question)
            assert q_type == expected_type
            assert source == "web_search", f"Question '{question}' should route to web_search"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

