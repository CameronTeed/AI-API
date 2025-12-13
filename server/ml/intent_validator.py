"""
ML-Based Intent Validator for Date Ideas Chat

Uses zero-shot classification to dynamically detect user intent without hardcoded keywords.
Replaces brittle keyword matching with semantic understanding.

Model: facebook/bart-large-mnli (zero-shot classification)
Approach: Classify user message against predefined intent categories
"""

import logging
from typing import Tuple, Dict, Optional

logger = logging.getLogger(__name__)

# Pre-trained zero-shot classifier
try:
    from transformers import pipeline
    INTENT_CLASSIFIER = pipeline(
        "zero-shot-classification",
        model="facebook/bart-large-mnli"
    )
    ML_INTENT_AVAILABLE = True
except ImportError:
    INTENT_CLASSIFIER = None
    ML_INTENT_AVAILABLE = False
    logger.warning("transformers not available, ML intent validation disabled")


class IntentValidator:
    """ML-based intent validation using zero-shot classification"""

    # Intent categories - no hardcoded keywords needed!
    INTENT_CATEGORIES = [
        "asking for new date ideas or suggestions",
        "asking about details of a specific venue",
        "rejecting or modifying a previous suggestion",
        "asking a follow-up question about previous suggestions",
        "greeting or casual chat",
        "off-topic question not related to dates",
    ]

    # Confidence threshold for accepting classification
    CONFIDENCE_THRESHOLD = 0.5

    @staticmethod
    def classify_intent(message: str) -> Tuple[str, float, Dict[str, float]]:
        """
        Classify user message intent using ML.

        Args:
            message: User's input message

        Returns:
            Tuple of (intent_category, confidence, all_scores)
            - intent_category: Top predicted intent
            - confidence: Confidence score (0-1)
            - all_scores: Dict of all intent scores
        """
        if not ML_INTENT_AVAILABLE or not INTENT_CLASSIFIER:
            logger.warning("ML classifier not available, cannot classify intent")
            return "unknown", 0.0, {}

        try:
            result = INTENT_CLASSIFIER(
                message,
                IntentValidator.INTENT_CATEGORIES,
                multi_class=False
            )

            # Extract results
            top_intent = result['labels'][0]
            top_score = result['scores'][0]

            # Build score dictionary
            all_scores = dict(zip(result['labels'], result['scores']))

            logger.info(
                f"Intent classification: '{top_intent}' "
                f"(confidence: {top_score:.2f}) for message: '{message[:60]}...'"
            )

            return top_intent, top_score, all_scores

        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            return "unknown", 0.0, {}

    @staticmethod
    def is_date_related(message: str) -> Tuple[bool, float]:
        """
        Check if message is date-related using ML.

        Args:
            message: User's input message

        Returns:
            Tuple of (is_date_related, confidence)
        """
        intent, confidence, scores = IntentValidator.classify_intent(message)

        # Date-related intents
        date_related_intents = {
            "asking for new date ideas or suggestions",
            "asking about details of a specific venue",
            "rejecting or modifying a previous suggestion",
            "asking a follow-up question about previous suggestions",
        }

        is_date_related = intent in date_related_intents
        return is_date_related, confidence

    @staticmethod
    def is_greeting(message: str) -> Tuple[bool, float]:
        """
        Check if message is a greeting using ML.

        Args:
            message: User's input message

        Returns:
            Tuple of (is_greeting, confidence)
        """
        intent, confidence, scores = IntentValidator.classify_intent(message)
        is_greeting = intent == "greeting or casual chat"
        return is_greeting, confidence

    @staticmethod
    def is_off_topic(message: str) -> Tuple[bool, float]:
        """
        Check if message is off-topic using ML.

        Args:
            message: User's input message

        Returns:
            Tuple of (is_off_topic, confidence)
        """
        intent, confidence, scores = IntentValidator.classify_intent(message)
        is_off_topic = intent == "off-topic question not related to dates"
        return is_off_topic, confidence

