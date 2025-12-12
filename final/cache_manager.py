# cache_manager.py
# Smart caching layer for vibe predictions and search results
# Reduces redundant computations and database queries

import hashlib
import json
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import db_manager

# In-memory cache with TTL (time-to-live)
_vibe_cache = {}  # {text_hash: (vibes, timestamp)}
_search_cache = {}  # {query_hash: (results, timestamp)}
_venue_cache = {}  # {venue_id: (venue_data, timestamp)}

CACHE_TTL_SECONDS = 3600  # 1 hour
VIBE_CACHE_TTL = 86400  # 24 hours for vibe predictions

def _hash_text(text: str) -> str:
    """Create a hash of text for caching"""
    return hashlib.md5(text.lower().encode()).hexdigest()

def _is_cache_valid(timestamp: float, ttl: int = CACHE_TTL_SECONDS) -> bool:
    """Check if cached item is still valid"""
    return (time.time() - timestamp) < ttl

def cache_vibe_prediction(text: str, vibes: List[str]) -> None:
    """Cache a vibe prediction"""
    text_hash = _hash_text(text)
    _vibe_cache[text_hash] = (vibes, time.time())

def get_cached_vibe_prediction(text: str) -> Optional[List[str]]:
    """Get cached vibe prediction if available"""
    text_hash = _hash_text(text)
    
    if text_hash in _vibe_cache:
        vibes, timestamp = _vibe_cache[text_hash]
        if _is_cache_valid(timestamp, VIBE_CACHE_TTL):
            return vibes
        else:
            del _vibe_cache[text_hash]
    
    return None

def cache_search_result(query: str, results: List[Dict]) -> None:
    """Cache a search result"""
    query_hash = _hash_text(query)
    _search_cache[query_hash] = (results, time.time())

def get_cached_search_result(query: str) -> Optional[List[Dict]]:
    """Get cached search result if available"""
    query_hash = _hash_text(query)
    
    if query_hash in _search_cache:
        results, timestamp = _search_cache[query_hash]
        if _is_cache_valid(timestamp):
            return results
        else:
            del _search_cache[query_hash]
    
    return None

def cache_venue(venue_id: str, venue_data: Dict) -> None:
    """Cache venue data"""
    _venue_cache[venue_id] = (venue_data, time.time())

def get_cached_venue(venue_id: str) -> Optional[Dict]:
    """Get cached venue if available"""
    if venue_id in _venue_cache:
        venue_data, timestamp = _venue_cache[venue_id]
        if _is_cache_valid(timestamp):
            return venue_data
        else:
            del _venue_cache[venue_id]
    
    return None

def clear_cache(cache_type: str = 'all') -> None:
    """Clear cache(s)"""
    global _vibe_cache, _search_cache, _venue_cache
    
    if cache_type in ('all', 'vibe'):
        _vibe_cache.clear()
    if cache_type in ('all', 'search'):
        _search_cache.clear()
    if cache_type in ('all', 'venue'):
        _venue_cache.clear()

def get_cache_stats() -> Dict:
    """Get cache statistics"""
    return {
        'vibe_predictions': len(_vibe_cache),
        'search_results': len(_search_cache),
        'venues': len(_venue_cache),
        'total_items': len(_vibe_cache) + len(_search_cache) + len(_venue_cache)
    }

def cleanup_expired_cache() -> int:
    """Remove expired items from cache"""
    removed = 0
    
    # Clean vibe cache
    expired_keys = [k for k, (_, ts) in _vibe_cache.items() 
                   if not _is_cache_valid(ts, VIBE_CACHE_TTL)]
    for k in expired_keys:
        del _vibe_cache[k]
        removed += 1
    
    # Clean search cache
    expired_keys = [k for k, (_, ts) in _search_cache.items() 
                   if not _is_cache_valid(ts)]
    for k in expired_keys:
        del _search_cache[k]
        removed += 1
    
    # Clean venue cache
    expired_keys = [k for k, (_, ts) in _venue_cache.items() 
                   if not _is_cache_valid(ts)]
    for k in expired_keys:
        del _venue_cache[k]
        removed += 1
    
    return removed

