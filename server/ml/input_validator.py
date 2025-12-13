"""
Bulletproof Input Validator for Date Ideas Chat

Validates user input BEFORE processing to ensure:
1. Input is not empty/whitespace
2. Input is not a greeting/casual chat (Hello, Hi, etc.)
3. Input is not a math/general knowledge question (5+5, what is X, etc.)
4. Input is actually asking for date ideas or related follow-up

Uses multi-layer validation:
- Layer 1: Basic format validation (length, whitespace)
- Layer 2: Greeting/casual chat detection (ML-based)
- Layer 3: Off-topic detection (pattern-based)
- Layer 4: Intent validation (ML-based, no hardcoded keywords)

ML-based intent detection replaces brittle keyword matching with semantic understanding.
"""

import logging
import re
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Import ML-based intent validator
try:
    from .intent_validator import IntentValidator, ML_INTENT_AVAILABLE
except ImportError:
    IntentValidator = None
    ML_INTENT_AVAILABLE = False
    logger.warning("IntentValidator not available, using fallback validation")


class InputValidator:
    """Bulletproof input validation for date ideas chat"""

    # Greeting patterns - casual chat that's not a date request
    GREETING_PATTERNS = {
        r"^(hello|hi|hey|greetings|what's up|sup|yo|howdy)(\s|!|\?)*$",
        r"^(good morning|good afternoon|good evening|good night)(\s|!|\?)*$",
        r"^(how are you|how are you doing|how's it going|what's up)(\s|!|\?)*$",
        r"^(thanks|thank you|thanks for|appreciate)(\s|!|\?)*$",
        r"^(bye|goodbye|see you|farewell|take care)(\s|!|\?)*$",
        r"^(hi|hey)\s+(there|you|buddy|friend)(\s|!|\?)*$",  # "Hi there", "Hey buddy", etc.
    }

    # Off-topic patterns - math, general knowledge, not date-related
    OFF_TOPIC_PATTERNS = {
        r"^\d+\s*[\+\-\*\/]\s*\d+",  # Math: 5+5, 10-3, etc.
        r"^what is|^who is|^when is|^where is|^why is|^how is",  # General knowledge questions
        r"^tell me about|^explain|^describe",  # General info requests
        r"^(weather|time|date|news|sports|politics|weather)",  # Current events
    }



    @staticmethod
    def validate(user_message: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate user input for date ideas chat.

        Args:
            user_message: The user's input message

        Returns:
            Tuple of (is_valid, error_message, metadata)
            - is_valid: True if input is valid for processing
            - error_message: Empty string if valid, otherwise user-friendly error message
            - metadata: Dict with validation details (intent_type, confidence, etc.)
        """
        metadata = {"validation_layers": []}

        # LAYER 1: Basic format validation
        layer1_result = InputValidator._validate_format(user_message)
        metadata["validation_layers"].append(layer1_result)
        if not layer1_result["passed"]:
            return False, layer1_result["error"], metadata

        # LAYER 2: Greeting/casual chat detection
        layer2_result = InputValidator._detect_greeting(user_message)
        metadata["validation_layers"].append(layer2_result)
        if not layer2_result["passed"]:
            return False, layer2_result["error"], metadata

        # LAYER 3: Off-topic detection
        layer3_result = InputValidator._detect_off_topic(user_message)
        metadata["validation_layers"].append(layer3_result)
        if not layer3_result["passed"]:
            return False, layer3_result["error"], metadata

        # LAYER 4: Intent validation (must be date-related)
        layer4_result = InputValidator._validate_intent(user_message)
        metadata["validation_layers"].append(layer4_result)
        if not layer4_result["passed"]:
            return False, layer4_result["error"], metadata

        logger.info(f"✅ Input validation passed: '{user_message[:80]}'")
        return True, "", metadata

    @staticmethod
    def _validate_format(message: str) -> Dict[str, Any]:
        """LAYER 1: Check basic format (length, whitespace)"""
        if not message or not message.strip():
            return {
                "passed": False,
                "error": "Please enter a message. I'm here to help you find amazing date ideas!",
                "reason": "empty_message"
            }

        if len(message.strip()) < 3:
            return {
                "passed": False,
                "error": "Your message is too short. Tell me more about what kind of date you're looking for!",
                "reason": "too_short"
            }

        return {"passed": True, "reason": "format_valid"}

    @staticmethod
    def _detect_greeting(message: str) -> Dict[str, Any]:
        """LAYER 2: Detect greetings and casual chat using ML"""
        msg_lower = message.lower().strip()

        # First try pattern matching (fast, for obvious greetings)
        for pattern in InputValidator.GREETING_PATTERNS:
            if re.match(pattern, msg_lower):
                return {
                    "passed": False,
                    "error": "I'm ready to help! What kind of date are you looking for? (e.g., 'romantic dinner', 'outdoor adventure', 'casual coffee')",
                    "reason": "greeting_detected"
                }

        # Use ML for more nuanced greeting detection
        if IntentValidator and ML_INTENT_AVAILABLE:
            is_greeting, confidence = IntentValidator.is_greeting(message)
            if is_greeting and confidence > 0.6:  # High confidence threshold
                return {
                    "passed": False,
                    "error": "I'm ready to help! What kind of date are you looking for? (e.g., 'romantic dinner', 'outdoor adventure', 'casual coffee')",
                    "reason": "greeting_detected_ml"
                }

        return {"passed": True, "reason": "not_greeting"}

    @staticmethod
    def _detect_off_topic(message: str) -> Dict[str, Any]:
        """LAYER 3: Detect off-topic messages (math, general knowledge)"""
        msg_lower = message.lower().strip()

        # Check against off-topic patterns
        for pattern in InputValidator.OFF_TOPIC_PATTERNS:
            if re.search(pattern, msg_lower):
                return {
                    "passed": False,
                    "error": "I'm specifically designed to help you find date ideas! Ask me about romantic dinners, fun activities, or venues in your area.",
                    "reason": "off_topic_detected"
                }

        return {"passed": True, "reason": "on_topic"}

    @staticmethod
    def _validate_intent(message: str) -> Dict[str, Any]:
        """LAYER 4: Validate that message is date-related using ML"""

        # Use ML-based intent validation (no hardcoded keywords!)
        if IntentValidator and ML_INTENT_AVAILABLE:
            is_date_related, confidence = IntentValidator.is_date_related(message)

            if is_date_related and confidence > 0.5:  # Moderate confidence threshold
                return {
                    "passed": True,
                    "reason": "date_related_ml",
                    "confidence": confidence
                }
            elif not is_date_related and confidence > 0.7:  # High confidence it's NOT date-related
                return {
                    "passed": False,
                    "error": "I'm specifically designed to help you find date ideas! Ask me about romantic dinners, fun activities, or venues in your area.",
                    "reason": "not_date_related_ml",
                    "confidence": confidence
                }

        # Fallback: if ML not available or low confidence, be permissive
        # (better to process and let LLM decide than reject valid requests)
        return {
            "passed": True,
            "reason": "intent_validation_fallback"
        }

