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


@router.post("/date-ideas", response_model=dict, dependencies=[Depends(verify_admin_token)])
async def create_date_idea(idea: DateIdea):
    """
    Create a new date idea in the database

    Requires admin authentication via Bearer token in Authorization header

    Example:
    ```
    curl -X POST http://localhost:8000/api/admin/date-ideas \
      -H "Authorization: Bearer your_admin_token" \
      -H "Content-Type: application/json" \
      -d '{
        "title": "Sunset Picnic at Parliament Hill",
        "description": "Romantic picnic with a view of Parliament Hill at sunset",
        "category": "romantic",
        "price_tier": 1,
        "duration_min": 120,
        "indoor": false,
        "city": "Ottawa",
        "website": "https://www.parliament.ca",
        "phone": "+1-613-555-1234",
        "latitude": 45.4215,
        "longitude": -75.6972,
        "tags": ["romantic", "outdoor", "picnic", "sunset"]
      }'
    ```
    """
    try:
        from ...tools.vector_search import get_vector_store
        from ...tools.chat_context_storage import get_chat_storage
        import json
        from datetime import datetime

        vector_store = get_vector_store()
        storage = get_chat_storage()

        # Add to vector store
        await vector_store.add_date_idea(
            name=idea.title,
            description=idea.description,
            city=idea.city,
            price_tier=idea.price_tier,
            duration_minutes=idea.duration_min,
            indoor=idea.indoor,
            categories=[idea.category],
            unique_features=idea.tags or []
        )

        # Also store in database if storage is available
        if storage and storage.pool:
            try:
                async with storage.pool.connection() as conn:
                    # Generate embedding for the idea
                    from ...core.ml_integration import get_ml_wrapper
                    ml_wrapper = get_ml_wrapper()
                    embedding_text = f"{idea.title} {idea.description} {idea.category}"
                    embedding = ml_wrapper.generate_embedding(embedding_text)

                    # Get or create location
                    location_result = await conn.execute(
                        """
                        SELECT location_id FROM location
                        WHERE city = %s LIMIT 1
                        """,
                        (idea.city,)
                    )
                    location_row = await location_result.fetchone()

                    if not location_row:
                        # Create new location
                        location_result = await conn.execute(
                            """
                            INSERT INTO location (name, city, lat, lon)
                            VALUES (%s, %s, %s, %s)
                            RETURNING location_id
                            """,
                            (idea.city, idea.city, idea.latitude or 0, idea.longitude or 0)
                        )
                        location_id = (await location_result.fetchone())[0]
                    else:
                        location_id = location_row[0]

                    # Insert event
                    await conn.execute(
                        """
                        INSERT INTO event
                        (title, description, price, location_id, created_time, modified_time,
                         is_ai_recommended, ai_score, popularity, duration_min, indoor,
                         website, phone, rating, review_count, embedding, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            idea.title,
                            idea.description,
                            idea.price_tier * 25,
                            location_id,
                            datetime.now(),
                            datetime.now(),
                            True,  # Mark as AI-recommended (admin-added)
                            100,   # High score for admin-added ideas
                            0,     # No reviews yet
                            idea.duration_min,
                            idea.indoor,
                            idea.website or '',
                            idea.phone or '',
                            4.5,   # Default rating
                            0,     # No reviews yet
                            embedding,
                            json.dumps({'source': 'admin', 'category': idea.category, 'tags': idea.tags or []})
                        )
                    )
                    logger.info(f"✅ Stored custom idea in database: {idea.title}")
            except Exception as db_error:
                logger.warning(f"Could not store in database: {db_error}, but added to vector store")

        return {
            "success": True,
            "message": f"Date idea '{idea.title}' created successfully",
            "idea": {
                "title": idea.title,
                "category": idea.category,
                "city": idea.city,
                "price_tier": idea.price_tier
            }
        }

    except Exception as e:
        logger.error(f"Error creating date idea: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/date-ideas/{idea_id}", response_model=dict, dependencies=[Depends(verify_admin_token)])
async def update_date_idea(idea_id: str, idea: DateIdea):
    """
    Update an existing date idea in the database

    Requires admin authentication via Bearer token in Authorization header
    """
    try:
        from ...tools.chat_context_storage import get_chat_storage
        from datetime import datetime
        import json

        storage = get_chat_storage()

        if storage and storage.pool:
            async with storage.pool.connection() as conn:
                # Update event
                await conn.execute(
                    """
                    UPDATE event
                    SET title = %s, description = %s, price = %s,
                        duration_min = %s, indoor = %s, website = %s, phone = %s,
                        modified_time = %s, metadata = %s
                    WHERE id = %s
                    """,
                    (
                        idea.title,
                        idea.description,
                        idea.price_tier * 25,
                        idea.duration_min,
                        idea.indoor,
                        idea.website or '',
                        idea.phone or '',
                        datetime.now(),
                        json.dumps({'source': 'admin', 'category': idea.category, 'tags': idea.tags or []}),
                        idea_id
                    )
                )
                logger.info(f"✅ Updated date idea: {idea.title}")

        return {
            "success": True,
            "message": f"Date idea '{idea.title}' updated successfully",
            "idea_id": idea_id
        }

    except Exception as e:
        logger.error(f"Error updating date idea: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/date-ideas/{idea_id}", response_model=dict, dependencies=[Depends(verify_admin_token)])
async def delete_date_idea(idea_id: str):
    """
    Delete a date idea from the database

    Requires admin authentication via Bearer token in Authorization header
    """
    try:
        from ...tools.chat_context_storage import get_chat_storage

        storage = get_chat_storage()

        if storage and storage.pool:
            async with storage.pool.connection() as conn:
                # Delete event
                await conn.execute(
                    "DELETE FROM event WHERE id = %s",
                    (idea_id,)
                )
                logger.info(f"✅ Deleted date idea: {idea_id}")

        return {
            "success": True,
            "message": f"Date idea deleted successfully",
            "idea_id": idea_id
        }

    except Exception as e:
        logger.error(f"Error deleting date idea: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/date-ideas", response_model=dict, dependencies=[Depends(verify_admin_token)])
async def list_date_ideas():
    """List all date ideas"""
    try:
        from ...tools.vector_search import get_vector_store

        vector_store = get_vector_store()

        # Get all venues from vector store
        results = await vector_store.search("", limit=1000)

        return {
            "success": True,
            "count": len(results),
            "ideas": results
        }

    except Exception as e:
        logger.error(f"Error listing date ideas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rate-limit-stats/{account_id}")
async def get_rate_limit_stats(
    account_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Get rate limit statistics for an account
    Requires admin token
    """
    if not verify_admin_token(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        from ...rate_limiting import get_rate_limiter

        rate_limiter = get_rate_limiter()
        stats = rate_limiter.get_account_stats(account_id)

        return {
            "account_id": account_id,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Error getting rate limit stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
