import asyncio
import json
import logging
import time
from typing import AsyncIterator, List, Dict, Any, Optional
import grpc
from grpc import aio

from .tools.vector_store import get_vector_store
from .tools.web_search import get_web_client
from .llm.engine import LLMEngine
from .schemas import StructuredAnswer, Option, Citation
from .utils import price_tier_to_symbol, build_logistics, detect_source, safe_url

# Import generated protobuf files
import chat_service_pb2
import chat_service_pb2_grpc

logger = logging.getLogger(__name__)

class ChatHandler(chat_service_pb2_grpc.AiOrchestratorServicer):
    """Handles AI orchestrator chat requests"""
    
    def __init__(self):
        logger.debug("🔧 Initializing ChatHandler")
        self.llm_engine = LLMEngine()
        logger.debug("✅ LLMEngine initialized")
        self.vector_store = get_vector_store()
        logger.debug("✅ Vector store initialized")
        self.web_client = get_web_client()
        logger.debug("✅ Web client initialized")
        # Track active chat sessions for kill functionality
        self.active_sessions = {}
        logger.info("🎯 ChatHandler fully initialized")

    async def Chat(
        self, 
        request_iterator: AsyncIterator[chat_service_pb2.ChatRequest],
        context: aio.ServicerContext
    ) -> AsyncIterator[chat_service_pb2.ChatDelta]:
        """Handle bidirectional streaming chat"""
        
        logger.info("🎯 [CHAT_START] New chat session initiated")
        
        # Will get session ID from the request
        session_id = None
        
        try:
            # Get the first (and expected only) request from the stream
            request = None
            async for req in request_iterator:
                if request is None:
                    request = req
                    # Extract session ID from request (fallback to generated if not provided)
                    session_id = req.session_id if req.session_id else f"session_{int(time.time())}_{id(context)}"
                    logger.info(f"📨 [REQUEST_RECEIVED] Chat request with {len(req.messages)} messages, session_id: {session_id}")
                    break  # We only process the first request
            
            if not request:
                logger.error("❌ [REQUEST_ERROR] No chat request received")
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT, 
                    "No chat request received"
                )
                return

            # Track this session
            self.active_sessions[session_id] = {
                'context': context,
                'start_time': time.time()
            }
            logger.info(f"📊 [SESSION_TRACKING] Session {session_id} added to active sessions")

            # LOG COMPLETE REQUEST DETAILS
            logger.info("📋 [REQUEST_DETAILS] Complete request breakdown:")
            
            # Extract request data
            messages = []
            for i, msg in enumerate(request.messages):
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
                logger.info(f"  📝 Message {i+1}: role='{msg.role}', content='{msg.content}'")

            constraints = None
            if request.constraints:
                constraints = {
                    "city": request.constraints.city,
                    "budgetTier": request.constraints.budgetTier,
                    "hours": request.constraints.hours,
                    "indoor": request.constraints.indoor,
                    "categories": list(request.constraints.categories)
                }
                logger.info(f"  🎯 Constraints: {constraints}")
            else:
                logger.info("  🎯 Constraints: None")

            user_location = None
            if request.userLocation:
                user_location = {
                    "lat": request.userLocation.lat,
                    "lon": request.userLocation.lon
                }
                logger.info(f"  📍 User location: {user_location}")
            else:
                logger.info("  📍 User location: None")

            # Prepare tool functions
            async def vector_search_wrapper(**kwargs):
                """Wrapper to make vector store search async-compatible"""
                logger.info(f"🔍 [VECTOR_SEARCH_REQUEST] Args: {kwargs}")
                results = self.vector_store.search(**kwargs)
                logger.info(f"📊 [VECTOR_SEARCH_RESPONSE] Returned {len(results)} results")
                
                # Log each result summary
                for i, result in enumerate(results):
                    logger.info(f"  🎯 Result {i+1}: '{result.get('title', 'No title')}' (score: {result.get('similarity_score', 'N/A'):.4f})")
                
                return {"items": results, "source": "vector_store"}

            async def web_search_wrapper(**kwargs):
                logger.info(f"🌐 [WEB_SEARCH_REQUEST] Args: {kwargs}")
                results = await self.web_client.web_search(**kwargs)
                logger.info(f"📊 [WEB_SEARCH_RESPONSE] Returned {len(results.get('items', []))} results")
                return results

            # Stream the LLM response with buffering to reduce message count
            logger.info("🤖 [LLM_STREAM_START] Starting LLM chat stream")
            full_response = ""
            chunk_count = 0
            buffer = ""
            buffer_size = 50  # Send chunks when buffer reaches this size
            
            async for text_chunk in self.llm_engine.run_chat(
                messages=messages,
                vector_search_func=vector_search_wrapper,
                web_search_func=web_search_wrapper,
                constraints=constraints,
                user_location=user_location
            ):
                full_response += text_chunk
                buffer += text_chunk
                chunk_count += 1
                
                # Send buffer when it reaches target size or on word boundaries
                if len(buffer) >= buffer_size or text_chunk.endswith((' ', '\n', '.', '!', '?', ',')):
                    if buffer.strip():  # Only send non-empty buffers
                        logger.debug(f"📤 [BUFFER_SEND] Sending buffered chunk: '{buffer[:50]}{'...' if len(buffer) > 50 else ''}'")
                        
                        delta = chat_service_pb2.ChatDelta(
                            session_id=session_id,
                            text_delta=buffer,
                            done=False
                        )
                        yield delta
                        buffer = ""
            
            # Send any remaining buffer content
            if buffer.strip():
                logger.debug(f"📤 [BUFFER_FINAL] Sending final buffer: '{buffer[:50]}{'...' if len(buffer) > 50 else ''}'")
                delta = chat_service_pb2.ChatDelta(
                    session_id=session_id,
                    text_delta=buffer,
                    done=False
                )
                yield delta

            logger.info(f"✅ [LLM_STREAM_COMPLETE] Raw chunks received: {chunk_count}, Total length: {len(full_response)}")
            logger.info(f"📝 [FULL_TEXT_RESPONSE] Complete text: {full_response}")
            
            # Try to extract structured answer from the full response
            logger.info("🔧 [EXTRACT_START] Extracting structured answer")
            structured_answer = self._extract_structured_answer(full_response)
            
            # Send final structured answer if available
            if structured_answer:
                logger.info(f"📋 [STRUCTURED_RESPONSE] Sending structured answer with {len(structured_answer.options)} options")
                
                # Log each option details
                for i, option in enumerate(structured_answer.options):
                    logger.info(f"  🎯 Option {i+1}: '{option.title}'")
                    logger.info(f"    💰 Price: {option.price}, 🕐 Duration: {option.duration_min} min")
                    logger.info(f"    📂 Categories: {list(option.categories)}")
                    logger.info(f"    🌐 Website: {option.website}")
                    logger.info(f"    📍 Source: {option.source}")
                    
                    if option.entity_references and option.entity_references.primary_entity:
                        primary = option.entity_references.primary_entity
                        logger.info(f"    🔗 Primary Entity: {primary.title} ({primary.type}) -> {primary.url}")
                        
                        for j, related in enumerate(option.entity_references.related_entities):
                            logger.info(f"      🔗 Related {j+1}: {related.title} ({related.type}) -> {related.url}")
                
                delta = chat_service_pb2.ChatDelta(
                    session_id=session_id,
                    structured=structured_answer,
                    done=False
                )
                yield delta

            # Send completion signal
            logger.info("🏁 [CHAT_END] Sending final done signal")
            delta = chat_service_pb2.ChatDelta(session_id=session_id, done=True)
            yield delta
            
            logger.info(f"🎉 [SESSION_COMPLETE] Chat session completed successfully. Total response length: {len(full_response)}")

        except Exception as e:
            logger.error(f"💥 [CHAT_ERROR] Chat failed: {e}", exc_info=True)
            await context.abort(
                grpc.StatusCode.INTERNAL, 
                f"Internal error: {str(e)}"
            )
        finally:
            # Clean up session tracking
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                logger.info(f"🧹 [SESSION_CLEANUP] Session {session_id} removed from active sessions")

    def _extract_structured_answer(self, response_text: str) -> Optional[chat_service_pb2.StructuredAnswer]:
        """Extract structured answer from LLM response"""
        try:
            logger.info("🔧 [EXTRACT_PARSING] Calling LLM engine to parse structured answer")
            
            # Try to parse JSON from the response
            structured_data = self.llm_engine.parse_structured_answer(response_text)
            
            if not structured_data:
                logger.warning("⚠️ [EXTRACT_EMPTY] LLM engine returned empty structured data")
                return None

            logger.info(f"📋 [EXTRACT_DATA] Parsed data: summary='{structured_data.get('summary', '')[:50]}...', options={len(structured_data.get('options', []))}")

            # Convert to protobuf format
            options = []
            for i, opt_data in enumerate(structured_data.get("options", [])):
                logger.info(f"  🎯 [OPTION_{i+1}_CONVERT] Converting: '{opt_data.get('title', 'No title')}'")
                
                citations = []
                for cite_data in opt_data.get("citations", []):
                    citation = chat_service_pb2.Citation(
                        url=cite_data.get("url", ""),
                        title=cite_data.get("title", "")
                    )
                    citations.append(citation)

                # Handle logistics field - convert to string if it's an object
                logistics_data = opt_data.get("logistics", "")
                website_url = opt_data.get("website", "")  # Default from top level
                
                if isinstance(logistics_data, dict):
                    # Extract website from logistics if present
                    if "website" in logistics_data and not website_url:
                        website_url = logistics_data["website"]
                    
                    # Convert dict to a readable string format
                    logistics_parts = []
                    if "website" in logistics_data:
                        logistics_parts.append(f"Website: {logistics_data['website']}")
                    if "phone" in logistics_data:
                        logistics_parts.append(f"Phone: {logistics_data['phone']}")
                    if "city_id" in logistics_data:
                        logistics_parts.append(f"City: {logistics_data['city_id']}")
                    logistics_str = " | ".join(logistics_parts) if logistics_parts else ""
                else:
                    logistics_str = str(logistics_data) if logistics_data else ""

                option = chat_service_pb2.Option(
                    title=opt_data.get("title", ""),
                    categories=opt_data.get("categories", []),
                    price=opt_data.get("price", ""),
                    duration_min=opt_data.get("duration_min", 0),
                    why_it_fits=opt_data.get("why_it_fits", ""),
                    logistics=logistics_str,
                    website=website_url,
                    source=opt_data.get("source", ""),
                    citations=citations
                )
                
                # Add entity references if available
                if "entity_references" in opt_data and opt_data["entity_references"]:
                    entity_refs = opt_data["entity_references"]
                    
                    # Build primary entity
                    primary = entity_refs.get("primary_entity", {})
                    primary_entity = chat_service_pb2.EntityReference(
                        id=primary.get("id", ""),
                        type=primary.get("type", ""),
                        title=primary.get("title", ""),
                        url=primary.get("url", "")
                    )
                    
                    # Build related entities
                    related_entities = []
                    for related in entity_refs.get("related_entities", []):
                        related_entity = chat_service_pb2.EntityReference(
                            id=related.get("id", ""),
                            type=related.get("type", ""),
                            title=related.get("title", ""),
                            url=related.get("url", "")
                        )
                        related_entities.append(related_entity)
                    
                    # Set entity references
                    option.entity_references.CopyFrom(chat_service_pb2.EntityReferences(
                        primary_entity=primary_entity,
                        related_entities=related_entities
                    ))
                
                options.append(option)
                logger.info(f"  ✅ [OPTION_{i+1}_DONE] Converted successfully")

            structured_answer = chat_service_pb2.StructuredAnswer(
                summary=structured_data.get("summary", ""),
                options=options
            )
            
            logger.info(f"🎉 [EXTRACT_SUCCESS] Successfully created structured answer with {len(options)} options")
            return structured_answer

        except Exception as e:
            logger.error(f"💥 [EXTRACT_ERROR] Could not extract structured answer: {e}", exc_info=True)
            return None

    async def KillChat(
        self, 
        request: chat_service_pb2.KillChatRequest,
        context: aio.ServicerContext
    ) -> chat_service_pb2.KillChatResponse:
        """Kill/terminate an active chat session"""
        
        logger.info(f"🔪 [KILL_CHAT] Kill request received for session: {request.session_id}")
        
        try:
            session_id = request.session_id if request.session_id else "default"
            reason = request.reason if request.reason else "User requested termination"
            
            # Check if session exists
            if session_id in self.active_sessions:
                # Cancel the session's tasks
                session_info = self.active_sessions[session_id]
                if 'context' in session_info:
                    await session_info['context'].abort(
                        grpc.StatusCode.CANCELLED,
                        f"Chat terminated: {reason}"
                    )
                
                # Remove from active sessions
                del self.active_sessions[session_id]
                
                logger.info(f"✅ [KILL_SUCCESS] Session {session_id} terminated successfully")
                return chat_service_pb2.KillChatResponse(
                    success=True,
                    message=f"Chat session '{session_id}' terminated successfully. Reason: {reason}"
                )
            else:
                logger.warning(f"⚠️ [KILL_WARNING] Session {session_id} not found")
                return chat_service_pb2.KillChatResponse(
                    success=False,
                    message=f"Chat session '{session_id}' not found or already terminated"
                )
                
        except Exception as e:
            logger.error(f"💥 [KILL_ERROR] Error killing chat session: {e}", exc_info=True)
            return chat_service_pb2.KillChatResponse(
                success=False,
                message=f"Error terminating chat session: {str(e)}"
            )

    async def HealthCheck(
        self, 
        request: chat_service_pb2.HealthCheckRequest,
        context: aio.ServicerContext
    ) -> chat_service_pb2.HealthCheckResponse:
        """Health check endpoint to verify service status"""
        
        logger.info("🩺 [HEALTH_CHECK] Health check requested")
        
        try:
            # Check various components
            health_details = {}
            overall_status = "healthy"
            
            # Check LLM engine
            try:
                if self.llm_engine:
                    health_details["llm_engine"] = "healthy"
                else:
                    health_details["llm_engine"] = "unhealthy"
                    overall_status = "degraded"
            except Exception as e:
                health_details["llm_engine"] = f"error: {str(e)}"
                overall_status = "degraded"
            
            # Check vector store
            try:
                if self.vector_store:
                    health_details["vector_store"] = "healthy"
                else:
                    health_details["vector_store"] = "unhealthy"
                    overall_status = "degraded"
            except Exception as e:
                health_details["vector_store"] = f"error: {str(e)}"
                overall_status = "degraded"
            
            # Check web client
            try:
                if self.web_client:
                    health_details["web_client"] = "healthy"
                else:
                    health_details["web_client"] = "unhealthy"
                    overall_status = "degraded"
            except Exception as e:
                health_details["web_client"] = f"error: {str(e)}"
                overall_status = "degraded"
            
            # Active sessions count
            health_details["active_sessions"] = str(len(self.active_sessions))
            
            timestamp = int(time.time())
            message = f"Service is {overall_status}"
            
            logger.info(f"✅ [HEALTH_CHECK_COMPLETE] Status: {overall_status}, Active sessions: {len(self.active_sessions)}")
            
            return chat_service_pb2.HealthCheckResponse(
                status=overall_status,
                message=message,
                timestamp=timestamp,
                details=health_details
            )
            
        except Exception as e:
            logger.error(f"💥 [HEALTH_CHECK_ERROR] Health check failed: {e}", exc_info=True)
            return chat_service_pb2.HealthCheckResponse(
                status="unhealthy",
                message=f"Health check failed: {str(e)}",
                timestamp=int(time.time()),
                details={"error": str(e)}
            )
