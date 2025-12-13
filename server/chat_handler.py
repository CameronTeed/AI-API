import logging
import time
from typing import AsyncIterator, Optional
import grpc
from grpc import aio

from .tools.vector_search import get_vector_store
from .tools.web_search import get_web_client
from .tools.agent_tools import get_agent_tools
from .tools.chat_context_storage import get_chat_storage
from .llm.engine import get_llm_engine
from .core.ml_integration import get_ml_wrapper
from .core.search_engine import get_search_engine

# Import generated protobuf files
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import chat_service_pb2
import chat_service_pb2_grpc

logger = logging.getLogger(__name__)

class EnhancedChatHandler(chat_service_pb2_grpc.AiOrchestratorServicer):
    """Enhanced AI orchestrator chat handler with agent tools and context storage"""

    def __init__(self):
        logger.debug("🔧 Initializing Enhanced ChatHandler")

        # Initialize vector store and web client FIRST (needed by LLM engine)
        self.vector_store = get_vector_store()
        logger.debug("✅ Vector store initialized")

        self.web_client = get_web_client()
        logger.debug("✅ Web client initialized")

        # Initialize main LLM engine with vector store and web client (optimized for cost-efficiency)
        self.llm_engine = get_llm_engine(vector_store=self.vector_store, web_client=self.web_client)
        logger.debug("✅ LLMEngine initialized (ML-first, cost-efficient)")

        # Initialize agent tools
        self.agent_tools = get_agent_tools()
        logger.debug("✅ Agent tools initialized")

        # Initialize ML and search services
        self.ml_wrapper = get_ml_wrapper()
        self.search_engine = get_search_engine(vector_store=self.vector_store, web_client=self.web_client)
        logger.debug("✅ ML and search services initialized")

        self.chat_storage = get_chat_storage()
        logger.debug("✅ Chat context storage initialized")

        # Track active chat sessions for kill functionality
        self.active_sessions = {}
        logger.info("🎯 Enhanced ChatHandler fully initialized with ML integration")

    async def setup_storage(self):
        """Setup chat storage tables"""
        try:
            await self.chat_storage.ensure_tables_exist()
            logger.info("✅ Chat storage tables setup complete")
        except Exception as e:
            logger.error(f"❌ Failed to setup chat storage: {e}")

    async def _vector_search_wrapper(self, **kwargs):
        """Wrapper to make vector store search async-compatible"""
        logger.info(f"🔍 [VECTOR_SEARCH_REQUEST] Args: {kwargs}")
        results = self.vector_store.search(**kwargs)
        logger.info(f"📊 [VECTOR_SEARCH_RESPONSE] Returned {len(results)} results")
        
        # Log each result summary
        for i, result in enumerate(results):
            logger.info(f"  🎯 Result {i+1}: '{result.get('title', 'No title')}' (score: {result.get('similarity_score', 'N/A'):.4f})")
        
        return {"items": results, "source": "vector_store"}

    async def _web_search_wrapper(self, **kwargs):
        logger.info(f"🌐 [WEB_SEARCH_REQUEST] Args: {kwargs}")
        results = await self.web_client.web_search(**kwargs)
        logger.info(f"📊 [WEB_SEARCH_RESPONSE] Returned {len(results.get('items', []))} results")
        return results

    async def Chat(
        self, 
        request_iterator: AsyncIterator[chat_service_pb2.ChatRequest],
        context: aio.ServicerContext
    ) -> AsyncIterator[chat_service_pb2.ChatDelta]:
        """Handle bidirectional streaming chat with enhanced agent tools"""
        
        logger.info("🎯 [ENHANCED_CHAT_START] New enhanced chat session initiated")
        
        # Will get session ID from the request
        session_id = None
        user_id = None
        
        try:
            # Get the first (and expected only) request from the stream
            request = None
            async for req in request_iterator:
                if request is None:
                    request = req
                    # Extract session ID from request (fallback to generated if not provided)
                    session_id = req.session_id if req.session_id else f"session_{int(time.time())}_{id(context)}"
                    # Extract user ID if available
                    user_id = getattr(req, 'user_id', None) or 'anonymous'
                    logger.info(f"📨 [REQUEST_RECEIVED] Enhanced chat request with {len(req.messages)} messages, session_id: {session_id}")
                    break  # We only process the first request
            
            if not request:
                logger.error("❌ [REQUEST_ERROR] No chat request received")
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT, 
                    "No chat request received"
                )
                return

            # Setup chat session in storage
            await self.chat_storage.create_session(
                session_id=session_id,
                user_id=user_id,
                metadata={
                    'client_info': 'enhanced_chat_handler',
                    'start_time': time.time()
                }
            )

            # Track this session
            self.active_sessions[session_id] = {
                'context': context,
                'start_time': time.time(),
                'user_id': user_id
            }
            logger.info(f"📊 [SESSION_TRACKING] Enhanced session {session_id} added to active sessions")

            # LOG COMPLETE REQUEST DETAILS
            logger.info("📋 [REQUEST_DETAILS] Complete enhanced request breakdown:")
            
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

            # Stream the LLM response with enhanced agent tools and ML integration
            logger.info("🤖 [ENHANCED_LLM_STREAM_START] Starting enhanced LLM chat stream with ML integration")
            full_response = ""
            chunk_count = 0
            buffer = ""
            buffer_size = 50  # Send chunks when buffer reaches this size

            # Use LLM engine for chat
            logger.info(f"🚀 Using LLM engine for chat")
            async for text_chunk in self.llm_engine.run_chat(
                messages=messages,
                agent_tools=self.agent_tools,
                session_id=session_id,
                constraints=constraints,
                user_location=user_location
            ):
                # Note: Removed external cancellation check during streaming to avoid database errors
                # The session will be deactivated in the finally block

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

            logger.info(f"✅ [ENHANCED_LLM_STREAM_COMPLETE] Raw chunks received: {chunk_count}, Total length: {len(full_response)}")
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
            logger.info("🏁 [ENHANCED_CHAT_END] Sending final done signal")
            delta = chat_service_pb2.ChatDelta(session_id=session_id, done=True)
            yield delta
            
            logger.info(f"🎉 [ENHANCED_SESSION_COMPLETE] Enhanced chat session completed successfully. Total response length: {len(full_response)}")

        except Exception as e:
            logger.error(f"💥 [ENHANCED_CHAT_ERROR] Enhanced chat failed: {e}", exc_info=True)
            # Don't call abort during streaming - just stop yielding
            # The client will detect the stream ended without a done signal
        finally:
            # Clean up session tracking
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                logger.info(f"🧹 [SESSION_CLEANUP] Enhanced session {session_id} removed from active sessions")
            
            # Deactivate session in storage
            if session_id and self.chat_storage:
                await self.chat_storage.deactivate_session(session_id)

    def _extract_structured_answer(self, response_text: str) -> Optional[chat_service_pb2.StructuredAnswer]:
        """Extract structured answer from LLM response"""
        try:
            logger.info("🔧 [EXTRACT_PARSING] Attempting to extract structured answer from response")

            # Check if LLMEngine has parse_structured_answer method
            if not hasattr(self.llm_engine, 'parse_structured_answer'):
                logger.info("ℹ️  [EXTRACT_SKIP] LLMEngine does not have parse_structured_answer method, skipping structured extraction")
                return None

            # Try to parse JSON from the response
            structured_data = self.llm_engine.parse_structured_answer(response_text)

            if not structured_data:
                logger.warning("⚠️ [EXTRACT_EMPTY] Enhanced LLM engine returned empty structured data")
                return None

            logger.info(f"📋 [EXTRACT_DATA] Parsed data: summary='{structured_data.get('summary', '')[:50]}...', options={len(structured_data.get('options', []))}")

            # Convert to protobuf format
            options = []
            for i, opt_data in enumerate(structured_data.get("options", [])):
                # Validate required fields
                title = opt_data.get("title", "").strip()
                if not title:
                    logger.warning(f"  ⚠️  [OPTION_{i+1}_SKIP] Skipping option with empty title")
                    continue

                logger.info(f"  🎯 [OPTION_{i+1}_CONVERT] Converting: '{title}'")

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

                # Ensure logistics is not empty
                if not logistics_str.strip():
                    logistics_str = "Contact for details"
                    logger.debug(f"  ℹ️  [OPTION_{i+1}] Using default logistics")

                option = chat_service_pb2.Option(
                    title=title,
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

    async def GetChatHistory(
        self, 
        request: chat_service_pb2.ChatHistoryRequest,
        context: aio.ServicerContext
    ) -> chat_service_pb2.ChatHistoryResponse:
        """Get chat history for a session or user"""
        
        logger.info(f"📚 [CHAT_HISTORY] History request for session: {request.session_id}")
        
        try:
            if request.session_id:
                # Get history for specific session
                messages = await self.chat_storage.get_session_messages(
                    session_id=request.session_id,
                    limit=request.limit if request.limit > 0 else None,
                    include_system=False
                )
                
                history_messages = []
                for msg in messages:
                    history_message = chat_service_pb2.ChatMessage(
                        role=msg['role'],
                        content=msg['content'],
                        timestamp=msg['timestamp']
                    )
                    history_messages.append(history_message)
                
                return chat_service_pb2.ChatHistoryResponse(
                    success=True,
                    messages=history_messages,
                    total_count=len(history_messages)
                )
            
            else:
                # Search across user's chat history
                search_results = await self.chat_storage.search_chat_history(
                    user_id=getattr(request, 'user_id', None),
                    query=getattr(request, 'search_query', None),
                    limit=request.limit if request.limit > 0 else 20
                )
                
                history_messages = []
                for result in search_results:
                    if result['message_content']:
                        history_message = chat_service_pb2.ChatMessage(
                            role=result['message_role'],
                            content=result['message_content'],
                            timestamp=result['message_timestamp']
                        )
                        history_messages.append(history_message)
                
                return chat_service_pb2.ChatHistoryResponse(
                    success=True,
                    messages=history_messages,
                    total_count=len(history_messages)
                )
                
        except Exception as e:
            logger.error(f"💥 [CHAT_HISTORY_ERROR] Error retrieving chat history: {e}", exc_info=True)
            return chat_service_pb2.ChatHistoryResponse(
                success=False,
                error_message=f"Error retrieving chat history: {str(e)}",
                messages=[],
                total_count=0
            )

    async def KillChat(
        self, 
        request: chat_service_pb2.KillChatRequest,
        context: aio.ServicerContext
    ) -> chat_service_pb2.KillChatResponse:
        """Kill/terminate an active chat session"""
        
        logger.info(f"🔪 [KILL_ENHANCED_CHAT] Kill request received for session: {request.session_id}")
        
        try:
            session_id = request.session_id if request.session_id else "default"
            reason = request.reason if request.reason else "User requested termination"
            
            # Always deactivate in storage first (stateless source of truth)
            db_success = await self.chat_storage.deactivate_session(session_id)
            
            # Check if session exists locally and abort it
            local_found = False
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
                local_found = True
                logger.info(f"✅ [KILL_LOCAL] Enhanced session {session_id} terminated locally")
            
            if db_success or local_found:
                logger.info(f"✅ [KILL_SUCCESS] Enhanced session {session_id} terminated successfully")
                return chat_service_pb2.KillChatResponse(
                    success=True,
                    message=f"Enhanced chat session '{session_id}' terminated successfully. Reason: {reason}"
                )
            else:
                logger.warning(f"⚠️ [KILL_WARNING] Enhanced session {session_id} not found")
                return chat_service_pb2.KillChatResponse(
                    success=False,
                    message=f"Enhanced chat session '{session_id}' not found or already terminated"
                )
                
        except Exception as e:
            logger.error(f"💥 [KILL_ERROR] Error killing enhanced chat session: {e}", exc_info=True)
            return chat_service_pb2.KillChatResponse(
                success=False,
                message=f"Error terminating enhanced chat session: {str(e)}"
            )

    async def HealthCheck(
        self, 
        request: chat_service_pb2.HealthCheckRequest,
        context: aio.ServicerContext
    ) -> chat_service_pb2.HealthCheckResponse:
        """Health check endpoint to verify enhanced service status"""
        
        logger.info("🩺 [ENHANCED_HEALTH_CHECK] Enhanced health check requested")
        
        try:
            # Check various components
            health_details = {}
            overall_status = "healthy"
            
            # Check enhanced LLM engine
            try:
                if self.llm_engine:
                    health_details["enhanced_llm_engine"] = "healthy"
                else:
                    health_details["enhanced_llm_engine"] = "unhealthy"
                    overall_status = "degraded"
            except Exception as e:
                health_details["enhanced_llm_engine"] = f"error: {str(e)}"
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
            
            # Check agent tools
            try:
                if self.agent_tools:
                    health_details["agent_tools"] = "healthy"
                else:
                    health_details["agent_tools"] = "unhealthy"
                    overall_status = "degraded"
            except Exception as e:
                health_details["agent_tools"] = f"error: {str(e)}"
                overall_status = "degraded"
            
            # Check chat storage
            try:
                if self.chat_storage:
                    health_details["chat_storage"] = "healthy"
                else:
                    health_details["chat_storage"] = "unhealthy"
                    overall_status = "degraded"
            except Exception as e:
                health_details["chat_storage"] = f"error: {str(e)}"
                overall_status = "degraded"
            
            # Active sessions count
            health_details["active_sessions"] = str(len(self.active_sessions))
            
            timestamp = int(time.time())
            message = f"Enhanced service is {overall_status}"
            
            logger.info(f"✅ [ENHANCED_HEALTH_CHECK_COMPLETE] Status: {overall_status}, Active sessions: {len(self.active_sessions)}")
            
            return chat_service_pb2.HealthCheckResponse(
                status=overall_status,
                message=message,
                timestamp=timestamp,
                details=health_details
            )
            
        except Exception as e:
            logger.error(f"💥 [ENHANCED_HEALTH_CHECK_ERROR] Enhanced health check failed: {e}", exc_info=True)
            return chat_service_pb2.HealthCheckResponse(
                status="unhealthy",
                message=f"Enhanced health check failed: {str(e)}",
                timestamp=int(time.time()),
                details={"error": str(e)}
            )

    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.agent_tools:
                await self.agent_tools.close()
            if self.chat_storage:
                await self.chat_storage.close()
            logger.info("🧹 Enhanced ChatHandler cleanup completed")
        except Exception as e:
            logger.error(f"Error during enhanced cleanup: {e}")

# Legacy handler for backwards compatibility
ChatHandler = EnhancedChatHandler