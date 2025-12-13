"""
Question Type Classifier for Follow-Up Questions

Classifies follow-up questions by type and routes them to appropriate data sources:
- Database (dietary, accessibility, parking, price)
- Google Places API (hours, phone, website)
- Web Search (reviews, atmosphere, general info)
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class QuestionClassifier:
    """Classify follow-up questions by type and determine data source"""

    # Question types with keywords and preferred data sources
    QUESTION_TYPES = {
        "hours": {
            "keywords": ["hours", "open", "close", "when", "time", "opening", "closing", "available"],
            "source": "google_places",
            "description": "Operating hours and availability"
        },
        "dietary": {
            "keywords": ["vegetarian", "vegan", "gluten", "dietary", "allergies", "allergy", "kosher", "halal"],
            "source": "database",
            "description": "Dietary options and restrictions"
        },
        "accessibility": {
            "keywords": ["wheelchair", "accessible", "ADA", "mobility", "disabled", "disability", "ramp"],
            "source": "database",
            "description": "Accessibility features"
        },
        "parking": {
            "keywords": ["parking", "park", "lot", "valet", "street parking"],
            "source": "database",
            "description": "Parking availability and options"
        },
        "phone": {
            "keywords": ["phone", "call", "contact", "number", "reach", "telephone"],
            "source": "google_places",
            "description": "Contact phone number"
        },
        "website": {
            "keywords": ["website", "online", "book", "reserve", "reservation", "url", "link"],
            "source": "google_places",
            "description": "Website and booking information"
        },
        "reviews": {
            "keywords": ["review", "rating", "opinion", "people say", "feedback", "comments", "what do people"],
            "source": "web_search",
            "description": "Customer reviews and ratings"
        },
        "price": {
            "keywords": ["cost", "price", "expensive", "cheap", "afford", "budget", "how much"],
            "source": "database",
            "description": "Pricing information"
        },
        "atmosphere": {
            "keywords": ["atmosphere", "vibe", "noise", "crowded", "quiet", "ambiance", "busy", "romantic"],
            "source": "web_search",
            "description": "Atmosphere and ambiance"
        },
        "menu": {
            "keywords": ["menu", "food", "eat", "cuisine", "dish", "what to order", "what to eat"],
            "source": "web_search",
            "description": "Menu and food options"
        },
        "kids": {
            "keywords": ["kids", "children", "family", "baby", "toddler", "kid friendly"],
            "source": "database",
            "description": "Kid-friendly features"
        },
        "dogs": {
            "keywords": ["dogs", "dog", "pets", "pet friendly", "dog friendly", "animals", "bring our"],
            "source": "database",
            "description": "Pet-friendly policies"
        },
    }

    @staticmethod
    def classify(question: str) -> Tuple[str, str, str]:
        """
        Classify a question and return (type, data_source, description)

        Args:
            question: User's follow-up question

        Returns:
            Tuple of (question_type, data_source, description)
            Example: ("dietary", "database", "Dietary options and restrictions")
        """
        msg_lower = question.lower()

        # Check each question type
        for q_type, config in QuestionClassifier.QUESTION_TYPES.items():
            for keyword in config["keywords"]:
                if keyword in msg_lower:
                    logger.info(
                        f"Classified question as '{q_type}' "
                        f"(keyword: '{keyword}', source: {config['source']})"
                    )
                    return q_type, config["source"], config["description"]

        # Default to web search for general questions
        logger.info("Question type not recognized, defaulting to web_search")
        return "general", "web_search", "General information"

    @staticmethod
    def get_all_types() -> dict:
        """Get all question types and their configurations"""
        return QuestionClassifier.QUESTION_TYPES

