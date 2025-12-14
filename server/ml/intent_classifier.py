"""
Explicit Intent Classifier - First-Class Feature

Classifies user requests into 4 primary intents:
1. PLAN_DATE - "Find me a romantic dinner"
2. REFINE_PLAN - "Can we add more vegetarian options?"
3. GENERAL_QUESTION - "What's the weather like?"
4. INFO_LOOKUP - "Tell me about this restaurant"

This is a cleaner, more explicit routing layer than the hybrid router.
"""

import logging
from enum import Enum
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to load ML models
try:
    from sentence_transformers import util
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    logger.warning("sentence-transformers not available")

try:
    from transformers import pipeline
    ZERO_SHOT_CLASSIFIER = pipeline(
        "zero-shot-classification",
        model="facebook/bart-large-mnli",
        device=-1  # CPU
    )
    NLI_AVAILABLE = True
except Exception as e:
    NLI_AVAILABLE = False
    logger.warning(f"Zero-shot classifier not available: {e}")


class Intent(Enum):
    """Primary intent types"""
    PLAN_DATE = "plan_date"           # New date planning request
    REFINE_PLAN = "refine_plan"       # Modify existing plan
    GENERAL_QUESTION = "general_question"  # Weather, info, etc
    INFO_LOOKUP = "info_lookup"       # Details about specific venue
    INVALID = "invalid"               # Empty, off-topic


@dataclass
class ClassificationResult:
    """Result of intent classification"""
    intent: Intent
    confidence: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


class IntentClassifier:
    """
    Explicit intent classifier for routing user requests.
    
    Supports 4 primary intents with high accuracy.
    """
    
    # Intent templates for embedding-based matching
    INTENT_TEMPLATES = {
        Intent.PLAN_DATE: [
            "Find me a date idea",
            "Plan a date for me",
            "Suggest a romantic dinner",
            "What should we do",
            "I want to go somewhere",
        ],
        Intent.REFINE_PLAN: [
            "Can we change this",
            "Add more options",
            "Remove this venue",
            "I don't like this",
            "Let's try something else",
        ],
        Intent.GENERAL_QUESTION: [
            "What's the weather",
            "Tell me about",
            "How do I get there",
            "What time does it open",
            "Is it expensive",
        ],
        Intent.INFO_LOOKUP: [
            "Tell me about this restaurant",
            "What's the rating",
            "Do they have vegetarian options",
            "Is it kid friendly",
            "What's their phone number",
        ],
    }
    
    @staticmethod
    def classify(
        user_message: str,
        conversation_history: Optional[list] = None
    ) -> ClassificationResult:
        """
        Classify user message into one of 4 intents.
        
        Args:
            user_message: The user's input
            conversation_history: Previous messages (optional)
            
        Returns:
            ClassificationResult with intent, confidence, and metadata
        """
        metadata = {
            "stages": [],
            "scores": {},
            "reasoning": ""
        }
        
        # Check for invalid input
        if not user_message or len(user_message.strip()) < 3:
            metadata["reasoning"] = "Input too short"
            return ClassificationResult(Intent.INVALID, 0.0, metadata)
        
        # Stage 1: Zero-shot classification (most accurate)
        if NLI_AVAILABLE:
            intent, confidence, stage_meta = IntentClassifier._classify_nli(user_message)
            metadata["stages"].append(stage_meta)
            metadata["scores"] = stage_meta.get("scores", {})
            
            if confidence > 0.7:
                metadata["reasoning"] = f"NLI classification (confidence: {confidence:.2f})"
                return ClassificationResult(intent, confidence, metadata)
        
        # Stage 2: Keyword-based fallback
        intent, confidence, stage_meta = IntentClassifier._classify_keywords(user_message)
        metadata["stages"].append(stage_meta)
        metadata["reasoning"] = f"Keyword classification (confidence: {confidence:.2f})"
        
        return ClassificationResult(intent, confidence, metadata)
    
    @staticmethod
    def _classify_nli(user_message: str) -> Tuple[Intent, float, Dict[str, Any]]:
        """Zero-shot NLI classification"""
        try:
            candidate_labels = [
                "asking for new date ideas or planning a date",
                "asking to modify or refine an existing plan",
                "asking a general question about weather, time, or logistics",
                "asking for information about a specific venue or restaurant",
            ]
            
            result = ZERO_SHOT_CLASSIFIER(user_message, candidate_labels, multi_label=False)
            
            intent_map = {
                0: Intent.PLAN_DATE,
                1: Intent.REFINE_PLAN,
                2: Intent.GENERAL_QUESTION,
                3: Intent.INFO_LOOKUP,
            }
            
            top_idx = result['labels'].index(result['labels'][0])
            confidence = result['scores'][0]
            intent = intent_map.get(top_idx, Intent.GENERAL_QUESTION)
            
            return intent, confidence, {
                "stage": "nli_classification",
                "scores": {
                    "plan_date": result['scores'][0],
                    "refine_plan": result['scores'][1],
                    "general_question": result['scores'][2],
                    "info_lookup": result['scores'][3],
                }
            }
        except Exception as e:
            logger.error(f"NLI classification error: {e}")
            return Intent.GENERAL_QUESTION, 0.5, {"stage": "nli_error", "error": str(e)}
    
    @staticmethod
    def _classify_keywords(user_message: str) -> Tuple[Intent, float, Dict[str, Any]]:
        """Keyword-based fallback classification"""
        msg_lower = user_message.lower()
        
        # Check for refine keywords
        refine_keywords = ["change", "remove", "add", "don't like", "try something", "instead", "different"]
        if any(kw in msg_lower for kw in refine_keywords):
            return Intent.REFINE_PLAN, 0.8, {"stage": "keyword_refine"}
        
        # Check for info lookup keywords
        info_keywords = ["tell me", "rating", "hours", "phone", "vegetarian", "kid friendly", "expensive"]
        if any(kw in msg_lower for kw in info_keywords):
            return Intent.INFO_LOOKUP, 0.75, {"stage": "keyword_info"}
        
        # Check for general question keywords
        question_keywords = ["weather", "how do i", "what time", "is it", "what's the"]
        if any(kw in msg_lower for kw in question_keywords):
            return Intent.GENERAL_QUESTION, 0.7, {"stage": "keyword_question"}
        
        # Check for plan date keywords
        plan_keywords = ["find", "suggest", "plan", "date", "dinner", "lunch", "activity", "should we"]
        if any(kw in msg_lower for kw in plan_keywords):
            return Intent.PLAN_DATE, 0.75, {"stage": "keyword_plan"}
        
        # Default to general question
        return Intent.GENERAL_QUESTION, 0.5, {"stage": "keyword_default"}

