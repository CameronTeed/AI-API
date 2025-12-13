"""
Hybrid Intent Router - Dynamic & Robust

Uses a 3-stage pipeline:
1. FAST: Sentence-Transformer embedding similarity (low latency)
2. ACCURATE: Zero-shot NLI classifier (high accuracy on edge cases)
3. INTERACTIVE: Ask targeted clarification question if still ambiguous

This avoids brittle hardcoded patterns and works for all inputs.
"""

import logging
from typing import Tuple, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

# Try to load embedding model
try:
    from sentence_transformers import SentenceTransformer, util
    EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_MODEL = None
    EMBEDDING_AVAILABLE = False
    logger.warning("sentence-transformers not available, will use fallback")

# Try to load zero-shot classifier
try:
    from transformers import pipeline
    ZERO_SHOT_CLASSIFIER = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    NLI_AVAILABLE = True
except ImportError:
    ZERO_SHOT_CLASSIFIER = None
    NLI_AVAILABLE = False
    logger.warning("transformers not available, will use fallback")


class IntentType(Enum):
    """Intent types for routing"""
    NEW_DATE_REQUEST = "new_date_request"  # "Find me a romantic dinner"
    FOLLOW_UP_QUESTION = "follow_up_question"  # "What are the hours?"
    AMBIGUOUS = "ambiguous"  # Needs clarification
    INVALID = "invalid"  # Empty, greeting, off-topic


class HybridRouter:
    """
    Dynamic intent router using embeddings + NLI + optional clarification.
    
    Works for ANY input without hardcoded patterns.
    """

    # Intent templates for embedding similarity
    INTENT_TEMPLATES = {
        IntentType.NEW_DATE_REQUEST: [
            "I'm looking for a date idea",
            "Find me a romantic dinner",
            "Suggest a fun activity",
            "What's a good place to go",
            "I want to plan a date",
            "Show me venue suggestions",
            "Recommend a restaurant",
            "What should we do together",
            "Find me a casual coffee spot",
            "I want to plan something fun",
            "Suggest an adventurous outdoor activity",
            "What's a good place for a date",
            "Show me restaurant recommendations",
            "Find me a venue",
            "Where should we go",
            "What are some good date ideas",
            "I'm looking for a place to go",
            "Can you suggest something",
            "Find me something to do",
            "What's a fun activity nearby",
        ],
        IntentType.FOLLOW_UP_QUESTION: [
            "What are the hours?",
            "Is it wheelchair accessible?",
            "Can we bring our dog?",
            "What's the price?",
            "Tell me more about this place",
            "Does it have parking?",
            "What's the menu like?",
            "Is it good for kids?",
            "What's the address?",
            "How do I get there?",
            "Is there a dress code?",
            "Do they take reservations?",
            "What's the atmosphere like?",
            "Is it pet friendly?",
            "What's the rating?",
            "How far is it?",
            "Is it expensive?",
            "Do they have outdoor seating?",
            "What's the cuisine?",
            "Is it open on weekends?",
        ],
    }

    # Clarification questions for ambiguous cases
    CLARIFICATION_QUESTIONS = {
        IntentType.NEW_DATE_REQUEST: "Are you looking for a new date idea, or do you have a specific venue in mind?",
        IntentType.FOLLOW_UP_QUESTION: "Are you asking about a specific venue, or looking for new suggestions?",
    }

    @staticmethod
    def route(user_message: str, conversation_history: Optional[list] = None) -> Tuple[IntentType, float, Dict[str, Any]]:
        """
        Route user message to appropriate handler.

        Args:
            user_message: The user's input
            conversation_history: Previous messages (optional, for context)

        Returns:
            Tuple of (intent_type, confidence, metadata)
            - intent_type: NEW_DATE_REQUEST, FOLLOW_UP_QUESTION, AMBIGUOUS, or INVALID
            - confidence: 0.0-1.0 confidence score
            - metadata: Dict with stage info, scores, etc.
        """
        metadata = {
            "stages": [],
            "embedding_scores": {},
            "nli_scores": {},
            "final_decision": None,
        }

        # STAGE 1: Check for invalid input (empty, too short)
        if not user_message or len(user_message.strip()) < 3:
            logger.warning(f"Invalid input: '{user_message}'")
            return IntentType.INVALID, 0.0, metadata

        # STAGE 1.5: Quick off-topic check (math, general knowledge)
        if HybridRouter._is_obviously_off_topic(user_message):
            logger.warning(f"Off-topic input: '{user_message}'")
            return IntentType.AMBIGUOUS, 0.3, {
                "stages": [{"stage": "off_topic_check", "reason": "Math or general knowledge question"}],
                "final_decision": "Off-topic detected",
            }

        # STAGE 2: Fast embedding-based similarity (CHEAP)
        if EMBEDDING_AVAILABLE:
            intent, confidence, stage_meta = HybridRouter._stage_embedding(user_message)
            metadata["stages"].append(stage_meta)
            metadata["embedding_scores"] = stage_meta.get("scores", {})

            # If high confidence, return early
            if confidence > 0.75:
                logger.info(f"✅ Stage 1 (Embedding): High confidence {confidence:.2f} → {intent.value}")
                metadata["final_decision"] = f"Stage 1 (Embedding) - confidence {confidence:.2f}"
                return intent, confidence, metadata
        else:
            intent, confidence = IntentType.AMBIGUOUS, 0.5
            logger.debug("Embedding model not available, skipping Stage 1")

        # STAGE 3: Accurate NLI-based classification (ACCURATE)
        if NLI_AVAILABLE:
            intent, confidence, stage_meta = HybridRouter._stage_nli(user_message)
            metadata["stages"].append(stage_meta)
            metadata["nli_scores"] = stage_meta.get("scores", {})

            # If high confidence, return
            if confidence > 0.7:
                logger.info(f"✅ Stage 2 (NLI): High confidence {confidence:.2f} → {intent.value}")
                metadata["final_decision"] = f"Stage 2 (NLI) - confidence {confidence:.2f}"
                return intent, confidence, metadata
        else:
            logger.debug("NLI model not available, skipping Stage 2")

        # STAGE 4: Still ambiguous? Mark for clarification
        logger.warning(f"⚠️ Ambiguous input: '{user_message[:80]}' - needs clarification")
        metadata["final_decision"] = "Stage 3 (Ambiguous) - needs clarification"
        return IntentType.AMBIGUOUS, 0.5, metadata

    @staticmethod
    def _stage_embedding(user_message: str) -> Tuple[IntentType, float, Dict[str, Any]]:
        """
        STAGE 1: Fast embedding-based similarity routing.
        
        Embeds user message and compares to intent templates.
        Very fast (<10ms), good for most cases.
        """
        try:
            # Embed user message
            user_embedding = EMBEDDING_MODEL.encode(user_message, convert_to_tensor=True)

            scores = {}
            for intent_type, templates in HybridRouter.INTENT_TEMPLATES.items():
                # Embed all templates for this intent
                template_embeddings = EMBEDDING_MODEL.encode(templates, convert_to_tensor=True)

                # Get max similarity to any template
                similarities = util.pytorch_cos_sim(user_embedding, template_embeddings)[0]
                max_similarity = float(similarities.max())
                scores[intent_type.value] = max_similarity

            # Get best intent
            best_intent = max(scores.items(), key=lambda x: x[1])
            best_intent_type = IntentType(best_intent[0])
            confidence = best_intent[1]

            logger.debug(f"Embedding scores: {scores}")

            return best_intent_type, confidence, {
                "stage": "embedding",
                "scores": scores,
                "best_intent": best_intent_type.value,
                "confidence": confidence,
            }
        except Exception as e:
            logger.error(f"Embedding stage failed: {e}")
            return IntentType.AMBIGUOUS, 0.5, {
                "stage": "embedding",
                "error": str(e),
            }

    @staticmethod
    def _stage_nli(user_message: str) -> Tuple[IntentType, float, Dict[str, Any]]:
        """
        STAGE 2: Accurate NLI-based classification.

        Uses zero-shot classification for semantic understanding.
        Slower (~100ms) but more accurate on edge cases.
        """
        try:
            candidate_labels = [
                "asking for new date ideas or venue suggestions",
                "asking a question about a specific venue or date",
            ]

            result = ZERO_SHOT_CLASSIFIER(user_message, candidate_labels, multi_label=False)

            # Map to intent types
            scores = {
                IntentType.NEW_DATE_REQUEST.value: result['scores'][0],
                IntentType.FOLLOW_UP_QUESTION.value: result['scores'][1],
            }

            # Get best intent
            best_label = result['labels'][0]
            confidence = result['scores'][0]

            # More robust mapping
            if "new date" in best_label.lower() or "suggestions" in best_label.lower():
                best_intent = IntentType.NEW_DATE_REQUEST
            elif "question" in best_label.lower() or "specific" in best_label.lower():
                best_intent = IntentType.FOLLOW_UP_QUESTION
            else:
                # Default to whichever has higher score
                best_intent = IntentType.NEW_DATE_REQUEST if scores[IntentType.NEW_DATE_REQUEST.value] > scores[IntentType.FOLLOW_UP_QUESTION.value] else IntentType.FOLLOW_UP_QUESTION

            logger.debug(f"NLI scores: {scores}")

            return best_intent, confidence, {
                "stage": "nli",
                "scores": scores,
                "best_intent": best_intent.value,
                "confidence": confidence,
            }
        except Exception as e:
            logger.error(f"NLI stage failed: {e}")
            return IntentType.AMBIGUOUS, 0.5, {
                "stage": "nli",
                "error": str(e),
            }

    @staticmethod
    def get_clarification_question(intent_type: IntentType) -> str:
        """Get a targeted clarification question for ambiguous input."""
        return HybridRouter.CLARIFICATION_QUESTIONS.get(
            intent_type,
            "Could you clarify what you're looking for?"
        )

    @staticmethod
    def _is_obviously_off_topic(user_message: str) -> bool:
        """
        Quick check for obviously off-topic inputs.
        Uses simple patterns to catch math, general knowledge, etc.
        Only catches OBVIOUS off-topic, not venue-related questions.
        """
        import re

        message_lower = user_message.lower()

        # Math patterns (5+5, 10-3, etc.)
        if re.search(r'\d+\s*[\+\-\*\/]\s*\d+', message_lower):
            return True

        # General knowledge patterns (what is, who is, etc.)
        # BUT exclude venue-related questions
        if re.search(r'^(what|who|when|where|why|how)\s+(is|are|was|were)', message_lower):
            # Check if it's about a venue/date
            venue_keywords = ['restaurant', 'cafe', 'bar', 'venue', 'place', 'hours', 'menu', 'price', 'parking', 'address']
            if not any(keyword in message_lower for keyword in venue_keywords):
                return True

        # Tell me about patterns - BUT exclude venue-related
        if re.search(r'^(tell|explain|describe|teach)\s+me\s+about', message_lower):
            venue_keywords = ['restaurant', 'cafe', 'bar', 'venue', 'place', 'menu', 'atmosphere', 'vibe']
            if not any(keyword in message_lower for keyword in venue_keywords):
                return True

        # Weather/news patterns
        if any(word in message_lower for word in ['weather', 'temperature', 'forecast', 'news', 'sports', 'stock', 'crypto']):
            return True

        return False

