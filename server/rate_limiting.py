"""
Account-based rate limiting for AI Orchestrator
Supports different rate limits for different account tiers
"""

import logging
import time
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AccountTier(Enum):
    """Account tier levels"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class RateLimitConfig:
    """Rate limit configuration for an account tier"""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    concurrent_requests: int
    description: str


# Rate limit configurations for each tier
TIER_CONFIGS: Dict[AccountTier, RateLimitConfig] = {
    AccountTier.FREE: RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        requests_per_day=500,
        concurrent_requests=1,
        description="Free tier: 10 req/min, 100 req/hour, 500 req/day"
    ),
    AccountTier.BASIC: RateLimitConfig(
        requests_per_minute=30,
        requests_per_hour=500,
        requests_per_day=5000,
        concurrent_requests=3,
        description="Basic tier: 30 req/min, 500 req/hour, 5000 req/day"
    ),
    AccountTier.PRO: RateLimitConfig(
        requests_per_minute=100,
        requests_per_hour=2000,
        requests_per_day=20000,
        concurrent_requests=10,
        description="Pro tier: 100 req/min, 2000 req/hour, 20000 req/day"
    ),
    AccountTier.ENTERPRISE: RateLimitConfig(
        requests_per_minute=500,
        requests_per_hour=10000,
        requests_per_day=100000,
        concurrent_requests=50,
        description="Enterprise tier: 500 req/min, 10000 req/hour, 100000 req/day"
    ),
}


class AccountRateLimiter:
    """Per-account rate limiter with multiple time windows"""
    
    def __init__(self):
        """Initialize rate limiter"""
        self.account_counters: Dict[str, Dict] = {}
    
    def get_tier_config(self, account_tier: str) -> RateLimitConfig:
        """Get rate limit config for account tier"""
        try:
            tier = AccountTier(account_tier.lower())
            return TIER_CONFIGS[tier]
        except (ValueError, KeyError):
            logger.warning(f"Unknown account tier: {account_tier}, using FREE")
            return TIER_CONFIGS[AccountTier.FREE]
    
    def check_rate_limit(
        self,
        account_id: str,
        account_tier: str = "free"
    ) -> tuple[bool, Optional[str]]:
        """
        Check if account has exceeded rate limits
        
        Returns:
            (allowed: bool, reason: Optional[str])
        """
        config = self.get_tier_config(account_tier)
        now = time.time()
        
        # Initialize counter for this account if needed
        if account_id not in self.account_counters:
            self.account_counters[account_id] = {
                "minute_window": {"count": 0, "reset_at": now + 60},
                "hour_window": {"count": 0, "reset_at": now + 3600},
                "day_window": {"count": 0, "reset_at": now + 86400},
                "concurrent": 0,
            }
        
        counter = self.account_counters[account_id]
        
        # Check and reset minute window
        if now >= counter["minute_window"]["reset_at"]:
            counter["minute_window"] = {"count": 0, "reset_at": now + 60}
        
        # Check and reset hour window
        if now >= counter["hour_window"]["reset_at"]:
            counter["hour_window"] = {"count": 0, "reset_at": now + 3600}
        
        # Check and reset day window
        if now >= counter["day_window"]["reset_at"]:
            counter["day_window"] = {"count": 0, "reset_at": now + 86400}
        
        # Check minute limit
        if counter["minute_window"]["count"] >= config.requests_per_minute:
            return False, f"Rate limit exceeded: {config.requests_per_minute} requests per minute"
        
        # Check hour limit
        if counter["hour_window"]["count"] >= config.requests_per_hour:
            return False, f"Rate limit exceeded: {config.requests_per_hour} requests per hour"
        
        # Check day limit
        if counter["day_window"]["count"] >= config.requests_per_day:
            return False, f"Rate limit exceeded: {config.requests_per_day} requests per day"
        
        # Check concurrent requests
        if counter["concurrent"] >= config.concurrent_requests:
            return False, f"Too many concurrent requests: max {config.concurrent_requests}"
        
        return True, None
    
    def consume_request(self, account_id: str) -> None:
        """Consume a request for the account"""
        if account_id in self.account_counters:
            counter = self.account_counters[account_id]
            counter["minute_window"]["count"] += 1
            counter["hour_window"]["count"] += 1
            counter["day_window"]["count"] += 1
    
    def increment_concurrent(self, account_id: str) -> None:
        """Increment concurrent request counter"""
        if account_id in self.account_counters:
            self.account_counters[account_id]["concurrent"] += 1
    
    def decrement_concurrent(self, account_id: str) -> None:
        """Decrement concurrent request counter"""
        if account_id in self.account_counters:
            self.account_counters[account_id]["concurrent"] = max(
                0, self.account_counters[account_id]["concurrent"] - 1
            )
    
    def get_account_stats(self, account_id: str) -> Dict:
        """Get rate limit stats for account"""
        if account_id not in self.account_counters:
            return {"error": "Account not found"}
        
        counter = self.account_counters[account_id]
        return {
            "minute_requests": counter["minute_window"]["count"],
            "hour_requests": counter["hour_window"]["count"],
            "day_requests": counter["day_window"]["count"],
            "concurrent_requests": counter["concurrent"],
        }


# Global rate limiter instance
_rate_limiter = AccountRateLimiter()


def get_rate_limiter() -> AccountRateLimiter:
    """Get global rate limiter instance"""
    return _rate_limiter

