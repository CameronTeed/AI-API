"""
ML Service API Endpoints
Exposes vibe prediction and date planning functionality via REST API
Integrated with search engine for comprehensive date planning
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from ..ml_service_integration import get_ml_service
from ..core.ml_integration import get_ml_wrapper
from ..core.search_engine import get_search_engine
from ..tools.vector_search import get_vector_store
from ..tools.web_search import get_web_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ml", tags=["ml-service"])

ml_service = get_ml_service()
ml_wrapper = get_ml_wrapper()

# Lazy-load search engine with proper initialization
def _get_search_engine():
    """Get search engine with proper vector store initialization"""
    vector_store = get_vector_store()
    web_client = get_web_client()
    return get_search_engine(vector_store=vector_store, web_client=web_client)


# Request/Response Models
class VibeRequest(BaseModel):
    """Request for vibe prediction"""
    text: str


class VibeResponse(BaseModel):
    """Response with predicted vibe"""
    text: str
    vibe: str


class BatchVibeRequest(BaseModel):
    """Request for batch vibe prediction"""
    texts: List[str]


class BatchVibeResponse(BaseModel):
    """Response with batch vibes"""
    vibes: List[str]


class DatePlanRequest(BaseModel):
    """Request for date planning"""
    preferences: Dict[str, Any]
    algorithm: str = "heuristic"  # "heuristic" or "genetic"


class DatePlanResponse(BaseModel):
    """Response with planned date"""
    plan: Optional[Dict[str, Any]]
    algorithm: str


# Endpoints
@router.post("/vibe/predict", response_model=VibeResponse)
async def predict_vibe(request: VibeRequest):
    """Predict vibe from text"""
    if not ml_service.available:
        raise HTTPException(status_code=503, detail="ML Service not available")
    
    try:
        vibe = ml_service.predict_vibe(request.text)
        return VibeResponse(text=request.text, vibe=vibe)
    except Exception as e:
        logger.error(f"Error predicting vibe: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vibe/predict-batch", response_model=BatchVibeResponse)
async def predict_vibes_batch(request: BatchVibeRequest):
    """Predict vibes for multiple texts"""
    if not ml_service.available:
        raise HTTPException(status_code=503, detail="ML Service not available")
    
    try:
        vibes = ml_service.predict_vibes_batch(request.texts)
        return BatchVibeResponse(vibes=vibes)
    except Exception as e:
        logger.error(f"Error predicting vibes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan/date", response_model=DatePlanResponse)
async def plan_date(request: DatePlanRequest):
    """Plan a date based on preferences"""
    if not ml_service.available:
        raise HTTPException(status_code=503, detail="ML Service not available")
    
    try:
        if request.algorithm == "genetic":
            plan = ml_service.plan_date_genetic(request.preferences)
        else:
            plan = ml_service.plan_date_heuristic(request.preferences)
        
        return DatePlanResponse(plan=plan, algorithm=request.algorithm)
    except Exception as e:
        logger.error(f"Error planning date: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def ml_service_health():
    """Check ML service health"""
    return {
        "status": "healthy" if ml_service.available else "unavailable",
        "ml_service_available": ml_service.available
    }


# Integrated endpoints combining search and ML
class IntegratedSearchRequest(BaseModel):
    """Request for integrated search with vibe filtering"""
    query: str
    limit: int = 10
    target_vibes: Optional[List[str]] = None


class IntegratedSearchResponse(BaseModel):
    """Response with search results and vibes"""
    results: List[Dict[str, Any]]
    predicted_vibes: List[str]
    count: int


@router.post("/search/integrated", response_model=IntegratedSearchResponse)
async def integrated_search(request: IntegratedSearchRequest):
    """Search with automatic vibe prediction and filtering"""
    try:
        # Predict vibes from query
        predicted_vibes = ml_wrapper.predict_vibe(request.query).split(', ')

        # Use target vibes if provided, otherwise use predicted
        target_vibes = request.target_vibes or predicted_vibes

        # Search with vibe filtering
        search_engine = _get_search_engine()
        results = await search_engine.vibe_filtered_search(
            request.query, target_vibes, request.limit
        )

        return IntegratedSearchResponse(
            results=results,
            predicted_vibes=predicted_vibes,
            count=len(results)
        )
    except Exception as e:
        logger.error(f"Integrated search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class DatePlanningRequest(BaseModel):
    """Request for comprehensive date planning"""
    query: str
    budget: Optional[float] = None
    duration: Optional[int] = None
    location: Optional[str] = None
    algorithm: str = "heuristic"


class DatePlanningResponse(BaseModel):
    """Response with date plan and search results"""
    plan: Optional[Dict[str, Any]]
    search_results: List[Dict[str, Any]]
    predicted_vibes: List[str]
    algorithm: str


@router.post("/plan/comprehensive", response_model=DatePlanningResponse)
async def comprehensive_date_planning(request: DatePlanningRequest):
    """Comprehensive date planning with search and ML"""
    try:
        # Predict vibes from query
        predicted_vibes = ml_wrapper.predict_vibe(request.query).split(', ')

        # Search for relevant venues
        search_engine = _get_search_engine()
        search_results = await search_engine.vibe_filtered_search(
            request.query, predicted_vibes, limit=20
        )

        # Build preferences for planning
        preferences = {
            'vibe': predicted_vibes,
            'budget': request.budget,
            'duration': request.duration,
            'location': request.location,
            'venues': search_results
        }

        # Plan date
        plan = ml_wrapper.plan_date(preferences, request.algorithm)

        return DatePlanningResponse(
            plan=plan,
            search_results=search_results,
            predicted_vibes=predicted_vibes,
            algorithm=request.algorithm
        )
    except Exception as e:
        logger.error(f"Comprehensive planning error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

