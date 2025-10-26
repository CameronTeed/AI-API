"""
Admin endpoints for managing date ideas
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class DateIdea(BaseModel):
    """Date idea model"""
    title: str
    description: str
    category: str
    price_tier: int  # 1-3
    duration_min: int
    indoor: bool
    city: str
    website: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tags: Optional[List[str]] = None


class DateIdeaResponse(BaseModel):
    """Response model for date idea"""
    id: int
    title: str
    description: str
    category: str
    price_tier: int
    duration_min: int
    indoor: bool
    city: str
    website: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tags: Optional[List[str]] = None


def verify_admin_token(authorization: Optional[str] = Header(None)) -> bool:
    """Verify admin token from Authorization header"""
    import os
    
    admin_token = os.getenv('ADMIN_TOKEN')
    if not admin_token:
        raise HTTPException(status_code=403, detail="Admin token not configured")
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    if token != admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    
    return True


@router.post("/date-ideas", response_model=DateIdeaResponse, dependencies=[Depends(verify_admin_token)])
async def create_date_idea(idea: DateIdea):
    """
    Create a new date idea in the database
    
    Requires admin authentication via Bearer token in Authorization header
    """
    try:
        from ...tools.db_client import get_db_client
        
        db_client = get_db_client()
        
        # Insert into database
        result = await db_client.execute(
            """
            INSERT INTO date_ideas 
            (title, description, category, price_tier, duration_min, indoor, city, website, phone, latitude, longitude, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, title, description, category, price_tier, duration_min, indoor, city, website, phone, latitude, longitude, tags
            """,
            (
                idea.title, idea.description, idea.category, idea.price_tier,
                idea.duration_min, idea.indoor, idea.city, idea.website, idea.phone,
                idea.latitude, idea.longitude, idea.tags
            )
        )
        
        if result:
            row = result[0]
            return DateIdeaResponse(
                id=row[0],
                title=row[1],
                description=row[2],
                category=row[3],
                price_tier=row[4],
                duration_min=row[5],
                indoor=row[6],
                city=row[7],
                website=row[8],
                phone=row[9],
                latitude=row[10],
                longitude=row[11],
                tags=row[12]
            )
        
        raise HTTPException(status_code=500, detail="Failed to create date idea")
    
    except Exception as e:
        logger.error(f"Error creating date idea: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/date-ideas/{idea_id}", response_model=DateIdeaResponse, dependencies=[Depends(verify_admin_token)])
async def get_date_idea(idea_id: int):
    """Get a specific date idea by ID"""
    try:
        from ...tools.db_client import get_db_client
        
        db_client = get_db_client()
        
        result = await db_client.execute(
            "SELECT id, title, description, category, price_tier, duration_min, indoor, city, website, phone, latitude, longitude, tags FROM date_ideas WHERE id = %s",
            (idea_id,)
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Date idea not found")
        
        row = result[0]
        return DateIdeaResponse(
            id=row[0],
            title=row[1],
            description=row[2],
            category=row[3],
            price_tier=row[4],
            duration_min=row[5],
            indoor=row[6],
            city=row[7],
            website=row[8],
            phone=row[9],
            latitude=row[10],
            longitude=row[11],
            tags=row[12]
        )
    
    except Exception as e:
        logger.error(f"Error retrieving date idea: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/date-ideas/{idea_id}", response_model=DateIdeaResponse, dependencies=[Depends(verify_admin_token)])
async def update_date_idea(idea_id: int, idea: DateIdea):
    """Update an existing date idea"""
    try:
        from ...tools.db_client import get_db_client
        
        db_client = get_db_client()
        
        result = await db_client.execute(
            """
            UPDATE date_ideas 
            SET title=%s, description=%s, category=%s, price_tier=%s, duration_min=%s, 
                indoor=%s, city=%s, website=%s, phone=%s, latitude=%s, longitude=%s, tags=%s
            WHERE id=%s
            RETURNING id, title, description, category, price_tier, duration_min, indoor, city, website, phone, latitude, longitude, tags
            """,
            (
                idea.title, idea.description, idea.category, idea.price_tier,
                idea.duration_min, idea.indoor, idea.city, idea.website, idea.phone,
                idea.latitude, idea.longitude, idea.tags, idea_id
            )
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Date idea not found")
        
        row = result[0]
        return DateIdeaResponse(
            id=row[0],
            title=row[1],
            description=row[2],
            category=row[3],
            price_tier=row[4],
            duration_min=row[5],
            indoor=row[6],
            city=row[7],
            website=row[8],
            phone=row[9],
            latitude=row[10],
            longitude=row[11],
            tags=row[12]
        )
    
    except Exception as e:
        logger.error(f"Error updating date idea: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/date-ideas/{idea_id}", dependencies=[Depends(verify_admin_token)])
async def delete_date_idea(idea_id: int):
    """Delete a date idea"""
    try:
        from ...tools.db_client import get_db_client
        
        db_client = get_db_client()
        
        await db_client.execute(
            "DELETE FROM date_ideas WHERE id = %s",
            (idea_id,)
        )
        
        return {"success": True, "message": f"Date idea {idea_id} deleted successfully"}
    
    except Exception as e:
        logger.error(f"Error deleting date idea: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

