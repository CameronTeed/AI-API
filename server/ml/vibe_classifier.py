"""
Vibe Classification - Zero-shot semantic classification using BART
Replaces hard-coded keyword matching
"""

from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Global model cache
_classifier = None

VIBE_LABELS = [
    "romantic", "energetic", "cozy", "fancy",
    "casual", "hipster", "historic", "outdoors",
    "artsy", "family", "foodie", "scenic", "wellness"
]

def _get_classifier():
    """Lazy load the zero-shot classifier"""
    global _classifier
    if _classifier is None:
        try:
            from transformers import pipeline
            _classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli"
            )
            logger.info("Loaded zero-shot classifier for vibes")
        except ImportError:
            logger.warning("transformers not available, vibe classification disabled")
            return None
    return _classifier

def classify_vibe(description: str, name: str = "") -> Optional[str]:
    """
    Classify venue vibe using zero-shot classification
    
    Args:
        description: Venue description
        name: Venue name (optional)
    
    Returns:
        Top vibe label, or None if classifier unavailable
    """
    classifier = _get_classifier()
    if classifier is None:
        return None
    
    try:
        text = f"{name} {description}".strip()
        if not text:
            return None
        
        result = classifier(text, VIBE_LABELS)
        return result['labels'][0]  # Top vibe
    except Exception as e:
        logger.error(f"Error classifying vibe: {e}")
        return None

def classify_vibe_with_scores(description: str, name: str = "") -> Optional[Dict[str, float]]:
    """
    Classify venue vibe with confidence scores
    
    Args:
        description: Venue description
        name: Venue name (optional)
    
    Returns:
        Dictionary mapping vibe labels to scores, or None if unavailable
    """
    classifier = _get_classifier()
    if classifier is None:
        return None
    
    try:
        text = f"{name} {description}".strip()
        if not text:
            return None
        
        result = classifier(text, VIBE_LABELS)
        return dict(zip(result['labels'], result['scores']))
    except Exception as e:
        logger.error(f"Error classifying vibe with scores: {e}")
        return None

def classify_vibe_batch(venues: List[Dict]) -> List[Tuple[Dict, Optional[str]]]:
    """
    Classify vibes for multiple venues
    
    Args:
        venues: List of venue dictionaries with 'name' and 'description'
    
    Returns:
        List of (venue, vibe) tuples
    """
    results = []
    for venue in venues:
        vibe = classify_vibe(
            venue.get('description', ''),
            venue.get('name', '')
        )
        results.append((venue, vibe))
    return results

def get_vibe_labels() -> List[str]:
    """Get list of available vibe labels"""
    return VIBE_LABELS.copy()

def add_vibe_label(label: str):
    """Add a new vibe label"""
    if label not in VIBE_LABELS:
        VIBE_LABELS.append(label)
        logger.info(f"Added vibe label: {label}")

def remove_vibe_label(label: str):
    """Remove a vibe label"""
    if label in VIBE_LABELS:
        VIBE_LABELS.remove(label)
        logger.info(f"Removed vibe label: {label}")

