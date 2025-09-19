import math
from typing import Optional

def price_tier_to_symbol(tier: int) -> str:
    """Convert price tier (1,2,3) to symbol ($,$$,$$$)"""
    symbols = {1: "$", 2: "$$", 3: "$$$"}
    return symbols.get(tier, "$")

def build_logistics(city: str, user_lat: Optional[float] = None, user_lon: Optional[float] = None) -> str:
    """Build logistics info based on city and user location"""
    if not city:
        return "Check local transportation options"
    
    # Basic logistics template
    if city.lower() in ["ottawa", "toronto", "montreal"]:
        return f"{city} downtown area, public transit accessible"
    else:
        return f"Located in {city}, check local transit"

def detect_source(db_used: bool, web_used: bool) -> str:
    """Determine the source based on what data was used"""
    if db_used and web_used:
        return "mixed"
    elif web_used:
        return "web"
    else:
        return "db"

def safe_url(website: Optional[str], fallback_url: Optional[str] = None) -> str:
    """Return a safe URL or fallback"""
    if website and website.startswith(("http://", "https://")):
        return website
    elif fallback_url:
        return fallback_url
    else:
        return ""

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers"""
    # Haversine formula
    R = 6371  # Earth's radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat/2) * math.sin(dlat/2) + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon/2) * math.sin(dlon/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c
