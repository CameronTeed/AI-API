"""
Chat endpoints for AI Orchestrator
Handles conversation with the agent for date ideas
Enhanced with ML service integration
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..models import ChatMessage, ChatRequest, ChatResponse, Constraints, Location
from ...core.ml_integration import get_ml_wrapper
from ...core.search_engine import get_search_engine

logger = logging.getLogger(__name__)

router = APIRouter()


class ConversationRequest(BaseModel):
    """Request for starting or continuing a conversation"""
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    messages: List[ChatMessage]
    constraints: Optional[Constraints] = None
    user_location: Optional[Location] = None


class ConversationResponse(BaseModel):
    """Response from conversation endpoint"""
    session_id: str
    response: str
    suggestions: Optional[List[str]] = None


@router.post("/conversation", response_model=ConversationResponse)
async def chat_conversation(request: ConversationRequest):
    """
    Start or continue a conversation with the AI agent

    The agent will:
    - Remember previous messages in the conversation
    - Use available tools (Google Places, SerpAPI, ScrapingBee, Vector DB)
    - Provide date ideas based on constraints
    - Maintain conversation context
    - Predict vibes and filter results accordingly
    - Integrate ML-based date planning
    """
    try:
        from ...chat_handler import EnhancedChatHandler

        # Use chat handler with optimized LLM engine
        handler = EnhancedChatHandler()

        # Convert messages to the format expected by the handler
        messages_data = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        # Prepare constraints
        constraints = None
        if request.constraints:
            constraints = {
                "city": request.constraints.city,
                "budgetTier": request.constraints.budget_tier,
                "hours": request.constraints.hours,
                "indoor": request.constraints.indoor,
                "categories": request.constraints.categories
            }

        # Prepare location
        user_location = None
        if request.user_location:
            user_location = {
                "lat": request.user_location.lat,
                "lon": request.user_location.lon
            }

        # Get response from LLM engine (optimized for cost-efficiency)
        full_response = ""
        async for chunk in handler.llm_engine.run_chat(
            messages=messages_data,
            agent_tools=handler.agent_tools,
            session_id=request.session_id,
            constraints=constraints,
            user_location=user_location
        ):
            full_response += chunk
        
        # Store conversation in chat storage
        if handler.chat_storage:
            await handler.chat_storage.add_message(
                session_id=request.session_id or "default",
                role="user",
                content=request.messages[-1].content if request.messages else ""
            )
            await handler.chat_storage.add_message(
                session_id=request.session_id or "default",
                role="assistant",
                content=full_response
            )
        
        return ConversationResponse(
            session_id=request.session_id or "default",
            response=full_response,
            suggestions=None
        )
    
    except Exception as e:
        logger.error(f"Chat conversation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=500)
):
    """
    Get chat history for a specific session
    
    Args:
        session_id: The session ID to retrieve history for
        limit: Maximum number of messages to return (default: 50, max: 500)
    """
    try:
        from ...chat_handler import EnhancedChatHandler
        
        handler = EnhancedChatHandler()
        
        if not handler.chat_storage:
            raise HTTPException(status_code=503, detail="Chat storage not available")
        
        messages = await handler.chat_storage.get_session_messages(
            session_id=session_id,
            limit=limit,
            include_system=False
        )
        
        return {
            "session_id": session_id,
            "messages": messages,
            "total_count": len(messages)
        }
    
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a chat session and its history
    
    Args:
        session_id: The session ID to delete
    """
    try:
        from ...chat_handler import EnhancedChatHandler
        
        handler = EnhancedChatHandler()
        
        if not handler.chat_storage:
            raise HTTPException(status_code=503, detail="Chat storage not available")
        
        await handler.chat_storage.deactivate_session(session_id)
        
        return {
            "success": True,
            "message": f"Session {session_id} deleted successfully"
        }
    
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

