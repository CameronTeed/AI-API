"""
Venue Type Classification - Zero-shot semantic classification
Replaces hard-coded type matching logic
"""

from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Global model cache
_classifier = None

TYPE_LABELS = [
    "restaurant", "cafe", "bar", "museum", "park",
    "shopping", "entertainment", "activity", "outdoor",
    "cultural", "nightlife", "casual dining", "fine dining",
    "fast food", "bakery", "dessert", "ice cream",
    "pizza", "italian", "asian", "mexican", "french",
    "sports", "fitness", "wellness", "spa", "yoga"
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
            logger.info("Loaded zero-shot classifier for types")
        except ImportError:
            logger.warning("transformers not available, type classification disabled")
            return None
    return _classifier

def classify_venue_types(description: str, name: str = "", 
                        threshold: float = 0.5) -> Optional[List[str]]:
    """
    Classify venue types using zero-shot classification
    
    Args:
        description: Venue description
        name: Venue name (optional)
        threshold: Minimum confidence threshold (0-1)
    
    Returns:
        List of type labels with confidence >= threshold, or None if unavailable
    """
    classifier = _get_classifier()
    if classifier is None:
        return None
    
    try:
        text = f"{name} {description}".strip()
        if not text:
            return None
        
        result = classifier(text, TYPE_LABELS, multi_class=True)
        
        # Return types with confidence >= threshold
        types = [label for label, score in zip(result['labels'], result['scores'])
                if score >= threshold]
        return types if types else None
    except Exception as e:
        logger.error(f"Error classifying types: {e}")
        return None

def classify_venue_types_with_scores(description: str, name: str = "") -> Optional[Dict[str, float]]:
    """
    Classify venue types with confidence scores
    
    Args:
        description: Venue description
        name: Venue name (optional)
    
    Returns:
        Dictionary mapping type labels to scores, or None if unavailable
    """
    classifier = _get_classifier()
    if classifier is None:
        return None
    
    try:
        text = f"{name} {description}".strip()
        if not text:
            return None
        
        result = classifier(text, TYPE_LABELS, multi_class=True)
        return dict(zip(result['labels'], result['scores']))
    except Exception as e:
        logger.error(f"Error classifying types with scores: {e}")
        return None

def classify_venue_types_batch(venues: List[Dict], 
                              threshold: float = 0.5) -> List[Tuple[Dict, Optional[List[str]]]]:
    """
    Classify types for multiple venues
    
    Args:
        venues: List of venue dictionaries
        threshold: Minimum confidence threshold
    
    Returns:
        List of (venue, types) tuples
    """
    results = []
    for venue in venues:
        types = classify_venue_types(
            venue.get('description', ''),
            venue.get('name', ''),
            threshold
        )
        results.append((venue, types))
    return results

def get_type_labels() -> List[str]:
    """Get list of available type labels"""
    return TYPE_LABELS.copy()

def add_type_label(label: str):
    """Add a new type label"""
    if label not in TYPE_LABELS:
        TYPE_LABELS.append(label)
        logger.info(f"Added type label: {label}")

def remove_type_label(label: str):
    """Remove a type label"""
    if label in TYPE_LABELS:
        TYPE_LABELS.remove(label)
        logger.info(f"Removed type label: {label}")

