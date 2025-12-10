"""
Geospatial service for enhanced location-based event searching
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
import psycopg
from dataclasses import dataclass

from ..db_config import get_db_pool

logger = logging.getLogger(__name__)

@dataclass
class GeographicArea:
    """Represents a geographic area/region"""
    area_id: int
    name: str
    area_type: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    radius_meters: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class LocationResult:
    """Result from a location-based search"""
    event_id: int
    title: str
    description: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    distance_meters: Optional[float] = None
    venue_name: Optional[str] = None
    address: Optional[str] = None
    price: Optional[float] = None
    rating: Optional[float] = None
    categories: List[str] = None

class GeospatialService:
    """Service for geospatial operations and location-based searches"""
    
    def __init__(self):
        self.db_pool = None
    
    async def initialize(self):
        """Initialize the geospatial service"""
        self.db_pool = await get_db_pool()
        logger.info("Geospatial service initialized")
    
    async def find_events_within_radius(
        self, 
        center_lat: float, 
        center_lon: float, 
        radius_meters: int,
        max_results: int = 50,
        filter_categories: Optional[List[str]] = None,
        filter_max_price: Optional[float] = None,
        include_expired: bool = False
    ) -> List[LocationResult]:
        """Find events within a radius of a center point"""
        if not self.db_pool:
            await self.initialize()
        
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT * FROM find_events_within_radius(%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        center_lat, center_lon, radius_meters, max_results,
                        filter_categories, filter_max_price, include_expired
                    )
                )
                
                results = await cursor.fetchall()
                
                events = []
                for row in results:
                    event_id, title, description, city, lat, lon, distance, venue_name, address, price, rating, categories = row
                    events.append(LocationResult(
                        event_id=event_id,
                        title=title,
                        description=description,
                        city=city,
                        lat=lat,
                        lon=lon,
                        distance_meters=distance,
                        venue_name=venue_name,
                        address=address,
                        price=float(price) if price else None,
                        rating=rating,
                        categories=categories or []
                    ))
                
                logger.info(f"Found {len(events)} events within {radius_meters}m of ({center_lat}, {center_lon})")
                return events
    
    async def find_events_in_bounding_box(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        max_results: int = 100,
        filter_categories: Optional[List[str]] = None,
        include_expired: bool = False
    ) -> List[LocationResult]:
        """Find events within a bounding box"""
        if not self.db_pool:
            await self.initialize()
        
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT * FROM find_events_in_bbox(%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (min_lat, min_lon, max_lat, max_lon, max_results, filter_categories, include_expired)
                )
                
                results = await cursor.fetchall()
                
                events = []
                for row in results:
                    event_id, title, city, lat, lon, venue_name, price, categories = row
                    events.append(LocationResult(
                        event_id=event_id,
                        title=title,
                        city=city,
                        lat=lat,
                        lon=lon,
                        venue_name=venue_name,
                        price=float(price) if price else None,
                        categories=categories or []
                    ))
                
                logger.info(f"Found {len(events)} events in bounding box")
                return events
    
    async def find_events_in_area(
        self,
        area_name: str,
        area_type: Optional[str] = None,
        max_results: int = 100,
        include_expired: bool = False
    ) -> List[LocationResult]:
        """Find events within a named geographic area"""
        if not self.db_pool:
            await self.initialize()
        
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT * FROM find_events_in_area(%s, %s, %s, %s)
                    """,
                    (area_name, area_type, max_results, include_expired)
                )
                
                results = await cursor.fetchall()
                
                events = []
                for row in results:
                    event_id, title, city, lat, lon, venue_name, found_area_name, found_area_type = row
                    events.append(LocationResult(
                        event_id=event_id,
                        title=title,
                        city=city,
                        lat=lat,
                        lon=lon,
                        venue_name=venue_name
                    ))
                
                logger.info(f"Found {len(events)} events in area '{area_name}'")
                return events
    
    async def find_nearby_events(
        self,
        source_event_id: int,
        radius_meters: int = 5000,
        max_results: int = 10,
        exclude_same_venue: bool = True
    ) -> List[Dict[str, Any]]:
        """Find events near another event"""
        if not self.db_pool:
            await self.initialize()
        
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT * FROM find_nearby_events(%s, %s, %s, %s)
                    """,
                    (source_event_id, radius_meters, max_results, exclude_same_venue)
                )
                
                results = await cursor.fetchall()
                
                nearby_events = []
                for row in results:
                    event_id, title, distance, venue_name, city, similarity_score = row
                    nearby_events.append({
                        "event_id": event_id,
                        "title": title,
                        "distance_meters": distance,
                        "venue_name": venue_name,
                        "city": city,
                        "similarity_score": similarity_score
                    })
                
                logger.info(f"Found {len(nearby_events)} events near event {source_event_id}")
                return nearby_events
    
    async def create_geographic_area(
        self,
        name: str,
        area_type: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        radius_meters: Optional[float] = None,
        polygon_coords: Optional[List[Tuple[float, float]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Create a new geographic area"""
        if not self.db_pool:
            await self.initialize()
        
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                # Build the geometry based on provided parameters
                geom_sql = None
                center_point_sql = None
                
                if polygon_coords:
                    # Create polygon from coordinates
                    coord_pairs = ', '.join([f"{lon} {lat}" for lat, lon in polygon_coords])
                    geom_sql = f"ST_SetSRID(ST_GeomFromText('POLYGON(({coord_pairs}, {polygon_coords[0][1]} {polygon_coords[0][0]}))'), 4326)"
                    # Calculate center of polygon
                    center_point_sql = f"ST_Centroid({geom_sql})"
                elif center_lat and center_lon:
                    center_point_sql = f"ST_SetSRID(ST_MakePoint({center_lon}, {center_lat}), 4326)"
                
                await cursor.execute(
                    f"""
                    INSERT INTO geographic_area (
                        name, area_type, city, state, country, 
                        geom, center_point, radius_meters, metadata
                    ) VALUES (%s, %s, %s, %s, %s, {geom_sql or 'NULL'}, {center_point_sql or 'NULL'}, %s, %s)
                    RETURNING area_id
                    """,
                    (name, area_type, city, state, country, radius_meters, metadata or {})
                )
                
                result = await cursor.fetchone()
                area_id = result[0] if result else None
                
                if area_id:
                    logger.info(f"Created geographic area '{name}' with ID {area_id}")
                    
                    # Auto-assign events to this new area
                    await self.assign_events_to_areas()
                
                return area_id
    
    async def get_geographic_areas(
        self,
        area_type: Optional[str] = None,
        city: Optional[str] = None
    ) -> List[GeographicArea]:
        """Get all geographic areas with optional filtering"""
        if not self.db_pool:
            await self.initialize()
        
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                where_clauses = []
                params = []
                
                if area_type:
                    where_clauses.append("area_type = %s")
                    params.append(area_type)
                
                if city:
                    where_clauses.append("city ILIKE %s")
                    params.append(f"%{city}%")
                
                where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"
                
                await cursor.execute(
                    f"""
                    SELECT 
                        area_id, name, area_type, city, state, country,
                        ST_Y(center_point) as center_lat,
                        ST_X(center_point) as center_lon,
                        radius_meters, metadata
                    FROM geographic_area
                    WHERE {where_sql}
                    ORDER BY area_type, name
                    """,
                    params
                )
                
                results = await cursor.fetchall()
                
                areas = []
                for row in results:
                    area_id, name, area_type, city, state, country, center_lat, center_lon, radius_meters, metadata = row
                    areas.append(GeographicArea(
                        area_id=area_id,
                        name=name,
                        area_type=area_type,
                        city=city,
                        state=state,
                        country=country,
                        center_lat=center_lat,
                        center_lon=center_lon,
                        radius_meters=radius_meters,
                        metadata=metadata
                    ))
                
                return areas
    
    async def assign_events_to_areas(self) -> Dict[str, Any]:
        """Auto-assign events to geographic areas based on location"""
        if not self.db_pool:
            await self.initialize()
        
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM assign_events_to_areas()")
                result = await cursor.fetchone()
                
                if result:
                    assigned_count, area_assignments = result
                    logger.info(f"Auto-assigned {assigned_count} event-area relationships")
                    return {
                        "assigned_count": assigned_count,
                        "assignments": area_assignments
                    }
                
                return {"assigned_count": 0, "assignments": []}
    
    async def get_geographic_statistics(self) -> Dict[str, Any]:
        """Get geographic statistics"""
        if not self.db_pool:
            await self.initialize()
        
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM get_geographic_statistics()")
                result = await cursor.fetchone()
                
                if result:
                    total_locations, locations_with_coords, total_areas, events_with_location, events_with_area_assignments, avg_events_per_city = result
                    return {
                        "total_locations": total_locations,
                        "locations_with_coords": locations_with_coords,
                        "total_areas": total_areas,
                        "events_with_location": events_with_location,
                        "events_with_area_assignments": events_with_area_assignments,
                        "avg_events_per_city": float(avg_events_per_city) if avg_events_per_city else 0.0,
                        "location_coverage_percent": round((locations_with_coords / max(total_locations, 1)) * 100, 2),
                        "area_assignment_percent": round((events_with_area_assignments / max(events_with_location, 1)) * 100, 2)
                    }
                
                return {}
    
    async def calculate_distance_between_events(self, event1_id: int, event2_id: int) -> Optional[float]:
        """Calculate distance between two events in meters"""
        if not self.db_pool:
            await self.initialize()
        
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT ST_Distance(
                        ST_Transform(l1.geom, 3857),
                        ST_Transform(l2.geom, 3857)
                    ) as distance_meters
                    FROM event e1
                    INNER JOIN location l1 ON e1.location_id = l1.location_id
                    CROSS JOIN event e2
                    INNER JOIN location l2 ON e2.location_id = l2.location_id
                    WHERE e1.event_id = %s AND e2.event_id = %s
                      AND l1.geom IS NOT NULL AND l2.geom IS NOT NULL
                    """,
                    (event1_id, event2_id)
                )
                
                result = await cursor.fetchone()
                return float(result[0]) if result and result[0] else None

# Global geospatial service instance
_geospatial_service = None

async def get_geospatial_service() -> GeospatialService:
    """Get global geospatial service instance"""
    global _geospatial_service
    if _geospatial_service is None:
        _geospatial_service = GeospatialService()
        await _geospatial_service.initialize()
    return _geospatial_service