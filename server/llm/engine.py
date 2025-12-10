import os
import json
import re
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncIterator
from openai import OpenAI
from .system_prompt import SYSTEM_PROMPT
from .tools_config import TOOLS_DEFINITION

logger = logging.getLogger(__name__)

class LLMEngine:
    def __init__(self):
        logger.debug("🔧 Initializing Enhanced LLMEngine with Agent Tools")
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("❌ OPENAI_API_KEY not found in environment")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        logger.debug(f"🔑 Using OpenAI API key: {api_key[:10]}...")
        self.client = OpenAI(api_key=api_key)
        logger.debug("✅ OpenAI client initialized")
        
        logger.debug("⚙️  Setting up enhanced tool definitions with agent capabilities")
        self.tools = TOOLS_DEFINITION

    def _trim_chat_messages(self, messages, max_chars=50000):
        """Trim chat messages to prevent token limit issues"""
        total_chars = sum(len(str(msg)) for msg in messages)
        
        if total_chars <= max_chars:
            return messages
        
        # Keep system messages and recent messages
        trimmed = []
        char_count = 0
        
        # Always keep system messages
        for msg in messages:
            if msg.get('role') == 'system':
                trimmed.append(msg)
                char_count += len(str(msg))
        
        # Add recent non-system messages from the end
        non_system_msgs = [msg for msg in messages if msg.get('role') != 'system']
        for msg in reversed(non_system_msgs):
            msg_size = len(str(msg))
            if char_count + msg_size <= max_chars:
                trimmed.insert(-len([m for m in trimmed if m.get('role') == 'system']), msg)
                char_count += msg_size
            else:
                break
        
        logger.debug(f"🔧 Trimmed messages from {total_chars} to {char_count} chars")
        return trimmed

    async def run_chat(
        self,
        messages: List[Dict[str, str]],
        vector_search_func=None,
        web_search_func=None,
        agent_tools=None,  # New agent tools manager
        chat_storage=None,  # Chat context storage
        session_id: Optional[str] = None,
        constraints: Optional[Dict] = None,
        user_location: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        """Run chat with enhanced agent tools and context storage"""
        
        logger.debug("🚀 Starting enhanced run_chat with agent tools")
        logger.debug(f"📝 Input messages: {len(messages)}")
        logger.debug(f"⚙️  Constraints: {constraints}")
        logger.debug(f"📍 User location: {user_location}")
        logger.debug(f"🔧 Agent tools available: {agent_tools is not None}")
        logger.debug(f"💾 Chat storage available: {chat_storage is not None}")
        
        # Store user message if chat storage is available
        if chat_storage and session_id and messages:
            latest_message = messages[-1]
            if latest_message.get('role') == 'user':
                await chat_storage.store_message(
                    session_id=session_id,
                    role='user',
                    content=latest_message.get('content', ''),
                    metadata={'constraints': constraints, 'user_location': user_location}
                )
        
        # Prepare messages with system prompt
        chat_messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ] + messages
        
        logger.debug(f"💭 System prompt length: {len(SYSTEM_PROMPT)}")

        # Add current date and time context
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        date_context = f"Current Date and Time: {current_time}. Use this for finding events, checking opening hours, and understanding 'today', 'tonight', or 'this weekend'."
        chat_messages.append({"role": "system", "content": date_context})
        logger.debug(f"📅 Added date context: {current_time}")

        # Add context about constraints and location if available
        if constraints or user_location:
            context = "User context: "
            if constraints:
                context += f"Constraints: {json.dumps(constraints)}. "
            if user_location:
                context += f"Location: {json.dumps(user_location)}."
            chat_messages.append({"role": "system", "content": context})
            logger.debug(f"📋 Added context: {context}")

        # Add aggressive multi-tool instruction
        multi_tool_instruction = """
CRITICAL INSTRUCTION: You MUST use multiple tools for this request. Start with:
1. search_date_ideas() to check database
2. search_featured_dates() for special content  
3. google_places_search() for real venues
4. enhanced_web_search() for current events
Use AT LEAST 3-4 tools before responding. NEVER stop after just one tool call.
"""
        chat_messages.append({"role": "system", "content": multi_tool_instruction})

        # Add chat history context if available
        if chat_storage and session_id:
            try:
                context_data = await chat_storage.get_session_context(session_id, context_length=5)
                if context_data and context_data.get('messages'):
                    recent_messages = context_data['messages'][-3:]  # Last 3 messages
                    if recent_messages:
                        context_summary = "Recent conversation context: "
                        for msg in recent_messages:
                            context_summary += f"{msg['role']}: {msg['content'][:100]}... "
                        chat_messages.append({"role": "system", "content": context_summary})
                        logger.debug("📚 Added recent conversation context")
            except Exception as e:
                logger.warning(f"Could not retrieve chat context: {e}")

        try:
            # Start the conversation with tools
            logger.debug("🤖 Making OpenAI API call with enhanced tools")
            # Trim messages to prevent token limit issues
            trimmed_messages = self._trim_chat_messages(chat_messages)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=trimmed_messages,
                tools=self.tools,
                tool_choice="auto",
                stream=False  # We'll handle streaming manually
            )
            
            logger.debug(f"✅ OpenAI response received. Finish reason: {response.choices[0].finish_reason}")

            # Track assistant message for storage
            assistant_message_content = ""

            # Check if tools were called
            if response.choices[0].message.tool_calls:
                logger.debug(f"🔧 Tool calls detected: {len(response.choices[0].message.tool_calls)}")
                # Process tool calls
                chat_messages.append(response.choices[0].message)

                # Store all tool results
                tool_results = {}

                # Execute tools in parallel for better performance
                logger.info(f"⚡ Executing {len(response.choices[0].message.tool_calls)} tools in parallel")
                tasks = []
                tool_calls_list = list(response.choices[0].message.tool_calls)

                for i, tool_call in enumerate(tool_calls_list):
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    logger.info(f"🔧 Queuing tool {i+1}/{len(tool_calls_list)}: {function_name}")

                    # Create task for parallel execution
                    task = asyncio.create_task(
                        self._execute_tool_call(
                            function_name,
                            function_args,
                            agent_tools,
                            vector_search_func,
                            web_search_func
                        )
                    )
                    # Store tool_call info with task for later reference
                    tasks.append((tool_call.id, function_name, function_args, task))

                # Wait for all tools to complete
                logger.info(f"⏳ Waiting for {len(tasks)} tools to complete...")
                for tool_call_id, function_name, function_args, task in tasks:
                    try:
                        tool_result = await task
                        tool_results[function_name] = tool_result
                        logger.debug(f"✅ Tool {function_name} completed")
                    except Exception as e:
                        logger.error(f"❌ Tool {function_name} failed: {e}")
                        tool_results[function_name] = {"error": str(e)}
                        tool_result = {"error": str(e)}

                    # Store tool call if storage is available
                    if chat_storage and session_id:
                        await chat_storage.store_tool_call(
                            session_id=session_id,
                            message_id=0,  # We'd need to track this better for real implementation
                            tool_name=function_name,
                            tool_arguments=function_args,
                            tool_result=tool_result
                        )

                    # Add tool result to messages
                    tool_message = {
                        "tool_call_id": tool_call_id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(tool_result)
                    }
                    chat_messages.append(tool_message)
                    logger.debug(f"📤 Added tool result to chat messages: {len(tool_message['content'])} chars")

                # FORCE ADDITIONAL TOOL CALLS if too few tools were called
                tools_called_count = len(response.choices[0].message.tool_calls)
                if tools_called_count < 3 and agent_tools:
                    logger.info(f"🚀 Only {tools_called_count} tool(s) called - forcing additional comprehensive search")
                    
                    # Extract query from user message for additional searches
                    user_query = ""
                    for msg in messages:
                        if msg.get('role') == 'user':
                            user_query = msg.get('content', '')
                            break
                    
                    # Determine city from constraints or query
                    city = "Ottawa"  # Default city
                    if constraints and constraints.get('city'):
                        city = constraints['city']
                    elif 'ottawa' in user_query.lower():
                        city = "Ottawa"
                    
                    # Extract query terms for searches
                    query_terms = user_query.replace('find me', '').replace('in ottawa', '').replace('in ', '').strip()
                    
                    # Force additional tool calls based on what wasn't called
                    additional_tools = []
                    called_tools = [tc.function.name for tc in response.choices[0].message.tool_calls]
                    
                    # Always ensure we use these core tools
                    if 'search_date_ideas' not in called_tools:
                        additional_tools.append(('search_date_ideas', {'query': user_query, 'city': city, 'top_k': 5}))
                    
                    if 'search_featured_dates' not in called_tools:
                        additional_tools.append(('search_featured_dates', {'city': city, 'category': 'adventure'}))
                    
                    if 'google_places_search' not in called_tools:
                        # Make query more specific with city context
                        location_specific_query = f"{query_terms} {city}"
                        additional_tools.append(('google_places_search', {'query': location_specific_query, 'location': f'{city}, Ontario, Canada'}))
                    
                    if 'enhanced_web_search' not in called_tools:
                        additional_tools.append(('enhanced_web_search', {'query': user_query, 'city': city, 'result_type': 'events'}))
                    
                    if 'eventbrite_search' not in called_tools:
                        additional_tools.append(('eventbrite_search', {'query': query_terms, 'city': city}))
                    
                    # Execute additional tools and add their results
                    additional_results_summary = []
                    for tool_name, tool_args in additional_tools[:3]:  # Limit to 3 additional tools to avoid token limits
                        logger.info(f"🔧 FORCE-CALLING additional tool: {tool_name} with args: {tool_args}")
                        
                        try:
                            # Execute the additional tool
                            additional_result = await self._execute_tool_call(
                                tool_name, 
                                tool_args, 
                                agent_tools,
                                vector_search_func,
                                web_search_func
                            )
                            
                            tool_results[tool_name] = additional_result
                            
                            # Add tool result to messages (simulate as if GPT called it)
                            fake_tool_call_id = f"force_{tool_name}_{id(additional_result)}"
                            tool_message = {
                                "tool_call_id": fake_tool_call_id,
                                "role": "tool",
                                "name": tool_name,
                                "content": json.dumps(additional_result)
                            }
                            chat_messages.append(tool_message)
                            
                            # Summarize result for logging
                            if additional_result.get('items'):
                                item_count = len(additional_result['items'])
                                additional_results_summary.append(f"{tool_name}: Found {item_count} results")
                            elif additional_result.get('results'):
                                item_count = len(additional_result['results'])
                                additional_results_summary.append(f"{tool_name}: Found {item_count} results")
                            else:
                                additional_results_summary.append(f"{tool_name}: Completed")
                            
                            logger.info(f"✅ Successfully executed additional tool: {tool_name}")
                            
                        except Exception as e:
                            logger.error(f"❌ Error executing additional tool {tool_name}: {e}")
                            additional_results_summary.append(f"{tool_name}: Error occurred")
                    
                    # Add a summary reminder as a system message
                    if additional_results_summary:
                        additional_context = {
                            "role": "system",
                            "content": f"I automatically ran these additional searches: {'; '.join(additional_results_summary)}. IMPORTANT: Combine ALL tool results (including these) in your response. Present findings from multiple sources together."
                        }
                        chat_messages.append(additional_context)

                # Get final response after tool execution
                logger.debug("🤖 Making final OpenAI API call with tool results")
                # Trim messages to prevent token limit issues
                trimmed_final_messages = self._trim_chat_messages(chat_messages)
                
                final_response = self.client.chat.completions.create(
                    model="gpt-4o",  # Use gpt-4o which has 128k context limit
                    messages=trimmed_final_messages,
                    stream=True
                )
                
                # Stream the final response
                for chunk in final_response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        assistant_message_content += content
                        yield content

            else:
                # No tools called, just stream the response
                # Trim messages to prevent token limit issues
                trimmed_no_tools_messages = self._trim_chat_messages(chat_messages)
                
                final_response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=trimmed_no_tools_messages,
                    stream=True
                )
                
                for chunk in final_response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        assistant_message_content += content
                        yield content

            # Store assistant response if chat storage is available
            if chat_storage and session_id and assistant_message_content:
                await chat_storage.store_message(
                    session_id=session_id,
                    role='assistant',
                    content=assistant_message_content,
                    metadata={'tool_calls_used': len(response.choices[0].message.tool_calls) if response.choices[0].message.tool_calls else 0}
                )

        except Exception as e:
            logger.error(f"Error in enhanced LLM chat: {e}")
            error_message = f"I encountered an error while processing your request: {str(e)}"
            
            # Store error message too
            if chat_storage and session_id:
                await chat_storage.store_message(
                    session_id=session_id,
                    role='assistant',
                    content=error_message,
                    metadata={'error': True, 'error_type': type(e).__name__}
                )
            
            yield error_message

    async def _execute_tool_call(
        self, 
        function_name: str, 
        function_args: Dict[str, Any],
        agent_tools=None,
        vector_search_func=None,
        web_search_func=None
    ) -> Dict[str, Any]:
        """Execute a tool call using the appropriate handler"""
        
        # Legacy vector search
        if function_name == "search_date_ideas":
            # Convert string parameters to proper types for vector search
            for param in ['max_price_tier', 'min_duration', 'max_duration', 'top_k']:
                if param in function_args and isinstance(function_args[param], str):
                    try:
                        function_args[param] = int(function_args[param])
                        logger.debug(f"🔧 Converted {param} from string to int: {function_args[param]}")
                    except (ValueError, TypeError):
                        logger.warning(f"⚠️  Could not convert {param} to int: {function_args[param]}")
            
            # Convert boolean parameters
            if 'indoor' in function_args and isinstance(function_args['indoor'], str):
                function_args['indoor'] = function_args['indoor'].lower() in ['true', '1', 'yes']
                logger.debug(f"🔧 Converted indoor from string to bool: {function_args['indoor']}")
            
            logger.debug("🔍 Executing vector search")
            return await vector_search_func(**function_args)
        
        # Legacy web search
        elif function_name == "web_search":
            logger.debug("🌐 Executing web search")
            return await web_search_func(**function_args)
        
        # Enhanced agent tools
        elif agent_tools:
            if function_name == "search_featured_dates":
                return await agent_tools.search_featured_dates(**function_args)
            elif function_name == "google_places_search":
                return await agent_tools.google_places_search(**function_args)
            elif function_name == "find_nearby_venues":
                return await agent_tools.find_nearby_venues(**function_args)
            elif function_name == "get_directions":
                return await agent_tools.get_directions(**function_args)
            elif function_name == "web_scrape_venue_info":
                return await agent_tools.web_scrape_venue_info(**function_args)
            elif function_name == "enhanced_web_search":
                return await agent_tools.enhanced_web_search(**function_args)
            elif function_name == "geocode_location":
                return await agent_tools.geocode_location(**function_args)
            elif function_name == "scrapingbee_scrape":
                return await agent_tools.scrapingbee_scrape(**function_args)
            elif function_name == "eventbrite_search":
                return await agent_tools.eventbrite_search(**function_args)
        
        # Unknown function
        logger.error(f"❌ Unknown function: {function_name}")
        return {"error": f"Unknown function: {function_name}"}

    def parse_structured_answer(self, content: str) -> Optional[Dict]:
        """Extract structured answer from the LLM response"""
        try:
            # 1. Try to find JSON within markdown code blocks (most reliable)
            code_block_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if code_block_match:
                logger.debug("🔍 Found JSON in markdown code block")
                return json.loads(code_block_match.group(1))

            # 2. Fallback: Try to find any JSON-like structure
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                logger.debug(f"🔍 Found raw JSON in response: {json_match.group()[:100]}...")
                return json.loads(json_match.group())
            
            # If no JSON found, try to extract structure from the natural language response
            logger.debug("🔍 No JSON found, attempting to extract structure from natural language")
            
            # Extract entity references in markdown format [Title](/api/path)
            entity_refs = re.findall(r'\[([^\]]+)\]\((/api/[^)]+)\)', content)
            logger.debug(f"🔗 Found {len(entity_refs)} entity references")
            
            # Create a basic structured response from the natural language
            lines = content.strip().split('\n')
            bullet_points = [line.strip('- ').strip() for line in lines if line.strip().startswith('-')]
            
            if bullet_points:
                # Create options from bullet points
                options = []
                for i, bullet in enumerate(bullet_points):
                    # Extract entity references for this bullet point
                    bullet_refs = re.findall(r'\[([^\]]+)\]\((/api/[^)]+)\)', bullet)
                    
                    # Determine primary entity (usually the first venue/business reference)
                    primary_entity = None
                    related_entities = []
                    
                    for title, url in bullet_refs:
                        entity_id = url.split('/')[-1]
                        entity_type = url.split('/')[-2]
                        
                        entity = {
                            "id": entity_id,
                            "type": entity_type,
                            "title": title,
                            "url": url
                        }
                        
                        # First venue/business becomes primary, others are related
                        if not primary_entity and entity_type in ['venues', 'businesses']:
                            primary_entity = entity
                        else:
                            related_entities.append(entity)
                    
                    option = {
                        "title": f"Option {i+1}",
                        "categories": [],
                        "price": "",
                        "duration_min": 0,
                        "why_it_fits": bullet.replace('[', '').replace(']', '').split('(')[0],  # Clean description
                        "logistics": "",
                        "website": "",
                        "source": "llm_extracted",
                        "entity_references": {
                            "primary_entity": primary_entity or {},
                            "related_entities": related_entities
                        },
                        "citations": []
                    }
                    options.append(option)
                
                return {
                    "summary": "Here are some date idea recommendations for you.",
                    "options": options
                }
            
        except Exception as e:
            logger.warning(f"Could not parse structured answer: {e}")
        return None