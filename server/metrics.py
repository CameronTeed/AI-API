"""
Metrics and Monitoring Module
Tracks application metrics for observability
"""

import logging
import time
from typing import Dict, Any, Callable
from functools import wraps
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects application metrics"""
    
    def __init__(self):
        """Initialize metrics collector"""
        self.start_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
        self.request_times = defaultdict(list)
        self.api_calls = defaultdict(int)
        self.cache_hits = 0
        self.cache_misses = 0
    
    def record_request(self, endpoint: str, duration: float, status: int):
        """Record API request"""
        self.request_count += 1
        self.request_times[endpoint].append(duration)
        if status >= 400:
            self.error_count += 1
    
    def record_api_call(self, api_name: str):
        """Record external API call"""
        self.api_calls[api_name] += 1
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record cache miss"""
        self.cache_misses += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Calculate average response times
        avg_times = {}
        for endpoint, times in self.request_times.items():
            if times:
                avg_times[endpoint] = sum(times) / len(times)
        
        # Calculate cache hit rate
        total_cache_ops = self.cache_hits + self.cache_misses
        cache_hit_rate = (self.cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0
        
        return {
            'uptime_seconds': uptime,
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate': (self.error_count / self.request_count * 100) if self.request_count > 0 else 0,
            'average_response_times': avg_times,
            'api_calls': dict(self.api_calls),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': cache_hit_rate,
            'timestamp': datetime.now().isoformat()
        }
    
    def reset(self):
        """Reset metrics"""
        self.request_count = 0
        self.error_count = 0
        self.request_times.clear()
        self.api_calls.clear()
        self.cache_hits = 0
        self.cache_misses = 0


# Global metrics instance
_metrics: MetricsCollector = None


def get_metrics() -> MetricsCollector:
    """Get global metrics instance"""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def track_request(endpoint: str):
    """Decorator to track request metrics"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                get_metrics().record_request(endpoint, duration, 200)
                return result
            except Exception as e:
                duration = time.time() - start
                get_metrics().record_request(endpoint, duration, 500)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                get_metrics().record_request(endpoint, duration, 200)
                return result
            except Exception as e:
                duration = time.time() - start
                get_metrics().record_request(endpoint, duration, 500)
                raise
        
        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def track_api_call(api_name: str):
    """Decorator to track external API calls"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            get_metrics().record_api_call(api_name)
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            get_metrics().record_api_call(api_name)
            return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

