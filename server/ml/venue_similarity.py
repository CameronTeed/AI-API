"""
Venue Similarity - Semantic similarity using pre-trained embeddings
Uses sentence-transformers for semantic understanding
"""

import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

# Global model cache
_model = None

def _get_model():
    """Lazy load the sentence-transformers model"""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Loaded sentence-transformers model")
        except ImportError:
            logger.warning("sentence-transformers not available, similarity disabled")
            return None
    return _model

def get_venue_embeddings(venue: Dict) -> np.ndarray:
    """
    Get semantic embeddings for a venue
    
    Args:
        venue: Venue dictionary with 'name' and 'description'
    
    Returns:
        Embedding vector (384-dimensional)
    """
    model = _get_model()
    if model is None:
        return None
    
    text = f"{venue.get('name', '')} {venue.get('description', '')}"
    return model.encode(text)

def get_venue_similarity(venue1: Dict, venue2: Dict) -> float:
    """
    Calculate semantic similarity between two venues (0-1)
    
    Args:
        venue1: First venue dictionary
        venue2: Second venue dictionary
    
    Returns:
        Similarity score (0-1), or None if model unavailable
    """
    model = _get_model()
    if model is None:
        return None
    
    try:
        text1 = f"{venue1.get('name', '')} {venue1.get('description', '')}"
        text2 = f"{venue2.get('name', '')} {venue2.get('description', '')}"
        
        emb1 = model.encode(text1)
        emb2 = model.encode(text2)
        
        # Cosine similarity
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = np.dot(emb1, emb2) / (norm1 * norm2)
        return float(similarity)
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        return None

def find_similar_venues(venue: Dict, candidates: List[Dict], 
                       threshold: float = 0.7) -> List[Tuple[Dict, float]]:
    """
    Find venues similar to a given venue
    
    Args:
        venue: Reference venue
        candidates: List of candidate venues
        threshold: Minimum similarity score (0-1)
    
    Returns:
        List of (venue, similarity_score) tuples, sorted by similarity
    """
    similar = []
    
    for candidate in candidates:
        similarity = get_venue_similarity(venue, candidate)
        if similarity is not None and similarity >= threshold:
            similar.append((candidate, similarity))
    
    # Sort by similarity descending
    similar.sort(key=lambda x: x[1], reverse=True)
    return similar

def get_diversity_penalty(venue: Dict, selected_venues: List[Dict]) -> float:
    """
    Calculate diversity penalty for a venue based on already selected venues
    
    Args:
        venue: Candidate venue
        selected_venues: Already selected venues
    
    Returns:
        Penalty score (0-1), where 1 = very similar to existing
    """
    if not selected_venues:
        return 0.0
    
    similarities = []
    for selected in selected_venues:
        sim = get_venue_similarity(venue, selected)
        if sim is not None:
            similarities.append(sim)
    
    if not similarities:
        return 0.0
    
    # Return average similarity as penalty
    return float(np.mean(similarities))

