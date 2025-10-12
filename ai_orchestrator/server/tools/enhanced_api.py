"""
Enhanced API endpoints for the new features:
1. Event expiry and cleanup management
2. Geospatial search capabilities  
3. Improved web search results
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ..tools.event_cleanup import get_cleanup_service, CleanupScheduler
from ..tools.geospatial import get_geospatial_service, SearchQuery as GeoSearchQuery
from ..tools.enhanced_web_search import get_enhanced_search_service, SearchQuery as WebSearchQuery

logger = logging.getLogger(__name__)

# Pydantic models for request/response validation
class SetExpiryRequest(BaseModel):
    event_id: int
    expiry_date: datetime
    auto_cleanup: bool = True

class RadiusSearchRequest(BaseModel):
    center_lat: float = Field(..., ge=-90, le=90)
    center_lon: float = Field(..., ge=-180, le=180)
    radius_meters: int = Field(..., gt=0, le=100000)  # Max 100km
    max_results: int = Field(50, ge=1, le=200)
    filter_categories: Optional[List[str]] = None
    filter_max_price: Optional[float] = None
    include_expired: bool = False

class BoundingBoxSearchRequest(BaseModel):
    min_lat: float = Field(..., ge=-90, le=90)
    min_lon: float = Field(..., ge=-180, le=180)
    max_lat: float = Field(..., ge=-90, le=90)
    max_lon: float = Field(..., ge=-180, le=180)
    max_results: int = Field(100, ge=1, le=500)
    filter_categories: Optional[List[str]] = None
    include_expired: bool = False

class AreaSearchRequest(BaseModel):
    area_name: str
    area_type: Optional[str] = None
    max_results: int = Field(100, ge=1, le=500)
    include_expired: bool = False

class CreateAreaRequest(BaseModel):
    name: str
    area_type: str  # 'neighborhood', 'district', 'city', 'county', 'custom'
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    center_lat: Optional[float] = Field(None, ge=-90, le=90)
    center_lon: Optional[float] = Field(None, ge=-180, le=180)
    radius_meters: Optional[float] = Field(None, gt=0, le=50000)
    polygon_coords: Optional[List[List[float]]] = None  # [[lat, lon], ...]
    metadata: Optional[Dict[str, Any]] = None

class EnhancedSearchRequest(BaseModel):
    query: str
    city: Optional[str] = None
    categories: Optional[List[str]] = None
    max_price: Optional[float] = None
    location_context: Optional[Dict[str, Any]] = None
    user_preferences: Optional[Dict[str, Any]] = None

class EnhancedAPIHandler:
    """API handler for enhanced features"""
    
    def __init__(self):
        self.cleanup_service = None
        self.geospatial_service = None
        self.web_search_service = None
        self.cleanup_scheduler = None
    
    async def initialize(self):
        """Initialize all services"""
        self.cleanup_service = await get_cleanup_service()
        self.geospatial_service = await get_geospatial_service()
        self.web_search_service = await get_enhanced_search_service()
        
        # Start cleanup scheduler (runs every 24 hours)
        self.cleanup_scheduler = CleanupScheduler(self.cleanup_service)
        self.cleanup_scheduler.start(interval_hours=24)
        
        logger.info("Enhanced API handler initialized")
    
    # =============================================================================
    # EVENT EXPIRY AND CLEANUP ENDPOINTS
    # =============================================================================
    
    async def set_event_expiry(self, request: SetExpiryRequest) -> Dict[str, Any]:
        """Set expiry date for an event"""
        success = await self.cleanup_service.set_event_expiry(
            request.event_id, 
            request.expiry_date, 
            request.auto_cleanup
        )
        
        return {
            "success": success,
            "event_id": request.event_id,
            "expiry_date": request.expiry_date.isoformat(),
            "auto_cleanup": request.auto_cleanup
        }
    
    async def restore_event(self, event_id: int) -> Dict[str, Any]:
        """Restore a soft-deleted event"""
        success = await self.cleanup_service.restore_event(event_id)
        
        return {
            "success": success,
            "event_id": event_id,
            "message": "Event restored successfully" if success else "Failed to restore event (may not exist or already active)"
        }
    
    async def run_manual_cleanup(self) -> Dict[str, Any]:
        """Manually trigger cleanup cycle"""
        results = await self.cleanup_service.run_cleanup_cycle()
        return results
    
    async def get_expiring_events(self, days_ahead: int = 7) -> Dict[str, Any]:
        """Get events expiring within specified days"""
        events = await self.cleanup_service.get_expiring_events(days_ahead)
        
        return {
            "days_ahead": days_ahead,
            "count": len(events),
            "events": events
        }
    
    async def get_cleanup_statistics(self) -> Dict[str, Any]:
        """Get cleanup statistics"""
        stats = await self.cleanup_service._get_cleanup_statistics()
        return stats
    
    async def get_cleanup_audit_log(self, limit: int = 100) -> Dict[str, Any]:
        """Get cleanup audit log"""
        audit_log = await self.cleanup_service.get_cleanup_audit_log(limit)
        
        return {
            "limit": limit,
            "count": len(audit_log),
            "audit_entries": audit_log
        }
    
    # =============================================================================
    # GEOSPATIAL SEARCH ENDPOINTS
    # =============================================================================
    
    async def find_events_within_radius(self, request: RadiusSearchRequest) -> Dict[str, Any]:
        """Find events within a radius of a center point"""
        events = await self.geospatial_service.find_events_within_radius(
            center_lat=request.center_lat,
            center_lon=request.center_lon,
            radius_meters=request.radius_meters,
            max_results=request.max_results,
            filter_categories=request.filter_categories,
            filter_max_price=request.filter_max_price,
            include_expired=request.include_expired
        )
        
        return {
            "search_params": request.dict(),
            "count": len(events),
            "events": [
                {
                    "event_id": event.event_id,
                    "title": event.title,
                    "description": event.description,
                    "city": event.city,
                    "lat": event.lat,
                    "lon": event.lon,
                    "distance_meters": round(event.distance_meters, 2) if event.distance_meters else None,
                    "venue_name": event.venue_name,
                    "address": event.address,
                    "price": float(event.price) if event.price else None,
                    "rating": event.rating,
                    "categories": event.categories
                }
                for event in events
            ]
        }
    
    async def find_events_in_bounding_box(self, request: BoundingBoxSearchRequest) -> Dict[str, Any]:
        """Find events within a bounding box"""
        events = await self.geospatial_service.find_events_in_bounding_box(
            min_lat=request.min_lat,
            min_lon=request.min_lon,
            max_lat=request.max_lat,
            max_lon=request.max_lon,
            max_results=request.max_results,
            filter_categories=request.filter_categories,
            include_expired=request.include_expired
        )
        
        return {
            "search_params": request.dict(),
            "count": len(events),
            "events": [
                {
                    "event_id": event.event_id,
                    "title": event.title,
                    "city": event.city,
                    "lat": event.lat,
                    "lon": event.lon,
                    "venue_name": event.venue_name,
                    "price": float(event.price) if event.price else None,
                    "categories": event.categories
                }
                for event in events
            ]
        }
    
    async def find_events_in_area(self, request: AreaSearchRequest) -> Dict[str, Any]:
        """Find events within a named geographic area"""
        events = await self.geospatial_service.find_events_in_area(
            area_name=request.area_name,
            area_type=request.area_type,
            max_results=request.max_results,
            include_expired=request.include_expired
        )
        
        return {
            "search_params": request.dict(),
            "count": len(events),
            "events": [
                {
                    "event_id": event.event_id,
                    "title": event.title,
                    "city": event.city,
                    "lat": event.lat,
                    "lon": event.lon,
                    "venue_name": event.venue_name
                }
                for event in events
            ]
        }
    
    async def find_nearby_events(self, source_event_id: int, radius_meters: int = 5000, 
                                max_results: int = 10, exclude_same_venue: bool = True) -> Dict[str, Any]:
        """Find events near another event"""
        nearby_events = await self.geospatial_service.find_nearby_events(
            source_event_id=source_event_id,
            radius_meters=radius_meters,
            max_results=max_results,
            exclude_same_venue=exclude_same_venue
        )
        
        return {
            "source_event_id": source_event_id,
            "radius_meters": radius_meters,
            "count": len(nearby_events),
            "nearby_events": nearby_events
        }
    
    async def create_geographic_area(self, request: CreateAreaRequest) -> Dict[str, Any]:
        """Create a new geographic area"""
        # Convert polygon coords if provided
        polygon_coords = None
        if request.polygon_coords:
            polygon_coords = [(lat, lon) for lat, lon in request.polygon_coords]
        
        area_id = await self.geospatial_service.create_geographic_area(
            name=request.name,
            area_type=request.area_type,
            city=request.city,
            state=request.state,
            country=request.country,
            center_lat=request.center_lat,
            center_lon=request.center_lon,
            radius_meters=request.radius_meters,
            polygon_coords=polygon_coords,
            metadata=request.metadata
        )
        
        return {
            "success": area_id is not None,
            "area_id": area_id,
            "name": request.name,
            "area_type": request.area_type
        }
    
    async def get_geographic_areas(self, area_type: Optional[str] = None, 
                                 city: Optional[str] = None) -> Dict[str, Any]:
        """Get all geographic areas with optional filtering"""
        areas = await self.geospatial_service.get_geographic_areas(area_type, city)
        
        return {
            "count": len(areas),
            "areas": [
                {
                    "area_id": area.area_id,
                    "name": area.name,
                    "area_type": area.area_type,
                    "city": area.city,
                    "state": area.state,
                    "country": area.country,
                    "center_lat": area.center_lat,
                    "center_lon": area.center_lon,
                    "radius_meters": area.radius_meters,
                    "metadata": area.metadata
                }
                for area in areas
            ]
        }
    
    async def assign_events_to_areas(self) -> Dict[str, Any]:
        """Auto-assign events to geographic areas"""
        result = await self.geospatial_service.assign_events_to_areas()
        return result
    
    async def get_geographic_statistics(self) -> Dict[str, Any]:
        """Get geographic statistics"""
        stats = await self.geospatial_service.get_geographic_statistics()
        return stats
    
    async def calculate_event_distance(self, event1_id: int, event2_id: int) -> Dict[str, Any]:
        """Calculate distance between two events"""
        distance = await self.geospatial_service.calculate_distance_between_events(event1_id, event2_id)
        
        return {
            "event1_id": event1_id,
            "event2_id": event2_id,
            "distance_meters": distance,
            "distance_km": round(distance / 1000, 2) if distance else None
        }
    
    # =============================================================================
    # ENHANCED WEB SEARCH ENDPOINTS
    # =============================================================================
    
    async def enhanced_web_search(self, request: EnhancedSearchRequest) -> Dict[str, Any]:
        """Perform enhanced web search"""
        search_query = WebSearchQuery(
            query=request.query,
            city=request.city,
            categories=request.categories or [],
            max_price=request.max_price,
            location_context=request.location_context,
            user_preferences=request.user_preferences
        )
        
        results = await self.web_search_service.enhanced_search(search_query)
        return results
    
    async def clear_search_cache(self) -> Dict[str, Any]:
        """Clear expired search cache entries"""
        cleared_count = await self.web_search_service.clear_expired_cache()
        
        return {
            "cleared_entries": cleared_count,
            "message": f"Cleared {cleared_count} expired cache entries"
        }
    
    async def get_search_cache_statistics(self) -> Dict[str, Any]:
        """Get search cache usage statistics"""
        stats = await self.web_search_service.get_cache_statistics()
        return stats
    
    # =============================================================================
    # COMBINED/INTEGRATED ENDPOINTS
    # =============================================================================
    
    async def comprehensive_search(self, query: str, city: Optional[str] = None,
                                 lat: Optional[float] = None, lon: Optional[float] = None,
                                 radius_meters: int = 10000) -> Dict[str, Any]:
        """Comprehensive search combining database events and web search"""
        results = {"database_events": [], "web_results": []}
        
        # Database search (geospatial if coordinates provided)
        if lat is not None and lon is not None:
            db_events = await self.geospatial_service.find_events_within_radius(
                center_lat=lat,
                center_lon=lon,
                radius_meters=radius_meters,
                max_results=20
            )
            results["database_events"] = [
                {
                    "event_id": event.event_id,
                    "title": event.title,
                    "description": event.description,
                    "distance_meters": round(event.distance_meters, 2) if event.distance_meters else None,
                    "venue_name": event.venue_name,
                    "source": "database"
                }
                for event in db_events
            ]
        
        # Web search
        web_search_query = WebSearchQuery(
            query=query,
            city=city,
            categories=[],
            location_context={"lat": lat, "lon": lon} if lat and lon else None
        )
        
        web_results = await self.web_search_service.enhanced_search(web_search_query)
        results["web_results"] = web_results.get("results", [])[:10]  # Top 10 web results
        
        # Combine and rank results
        all_results = []
        
        # Add database events with high base score
        for event in results["database_events"]:
            event["source"] = "database"
            event["combined_score"] = 0.8 + (0.2 if event["distance_meters"] and event["distance_meters"] < 2000 else 0)
            all_results.append(event)
        
        # Add web results with their scores
        for result in results["web_results"]:
            result["source"] = "web"
            all_results.append(result)
        
        # Sort by combined score
        all_results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        
        return {
            "query": query,
            "city": city,
            "location": {"lat": lat, "lon": lon} if lat and lon else None,
            "total_results": len(all_results),
            "database_count": len(results["database_events"]),
            "web_count": len(results["web_results"]),
            "combined_results": all_results[:25]  # Top 25 combined results
        }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        health = {
            "timestamp": datetime.now().isoformat(),
            "cleanup_service": "operational",
            "geospatial_service": "operational", 
            "web_search_service": "operational",
            "cleanup_scheduler_running": self.cleanup_scheduler.running if self.cleanup_scheduler else False
        }
        
        try:
            # Test cleanup service
            await self.cleanup_service._get_cleanup_statistics()
        except Exception as e:
            health["cleanup_service"] = f"error: {str(e)}"
        
        try:
            # Test geospatial service
            await self.geospatial_service.get_geographic_statistics()
        except Exception as e:
            health["geospatial_service"] = f"error: {str(e)}"
        
        try:
            # Test web search service
            await self.web_search_service.get_cache_statistics()
        except Exception as e:
            health["web_search_service"] = f"error: {str(e)}"
        
        return health

# Global enhanced API handler instance
_api_handler = None

async def get_enhanced_api_handler() -> EnhancedAPIHandler:
    """Get global enhanced API handler instance"""
    global _api_handler
    if _api_handler is None:
        _api_handler = EnhancedAPIHandler()
        await _api_handler.initialize()
    return _api_handler