import os
import json
import logging
from typing import List, Dict, Any, Optional, Iterator
from openai import OpenAI
from .system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class LLMEngine:
    def __init__(self):
        logger.debug("🔧 Initializing LLMEngine")
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("❌ OPENAI_API_KEY not found in environment")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        logger.debug(f"🔑 Using OpenAI API key: {api_key[:10]}...")
        self.client = OpenAI(api_key=api_key)
        logger.debug("✅ OpenAI client initialized")
        
        logger.debug("⚙️  Setting up tool definitions")
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_date_ideas",
                    "description": "Search the vector knowledge base for date ideas using semantic similarity and filters.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Natural language query describing the desired date idea"},
                            "city": {"type": "string", "description": "City to filter by"},
                            "max_price_tier": {"type": "integer", "enum": [1, 2, 3], "description": "Maximum price tier (1=budget, 2=moderate, 3=expensive)"},
                            "indoor": {"type": "boolean", "description": "Whether the activity should be indoors"},
                            "categories": {"type": "array", "items": {"type": "string"}, "description": "Categories to filter by (e.g., romantic, outdoor, food)"},
                            "min_duration": {"type": "integer", "description": "Minimum duration in minutes"},
                            "max_duration": {"type": "integer", "description": "Maximum duration in minutes"},
                            "top_k": {"type": "integer", "default": 10, "description": "Number of results to return"}
                        },
                        "required": ["query"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Targeted web search for venue hours, tickets, or new events. Return top 3 items with title/url/snippet/published_at.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "city": {"type": "string"}
                        },
                        "required": ["query"],
                        "additionalProperties": False
                    }
                }
            }
        ]

    async def run_chat(
        self,
        messages: List[Dict[str, str]],
        vector_search_func=None,
        web_search_func=None,
        constraints: Optional[Dict] = None,
        user_location: Optional[Dict] = None
    ) -> Iterator[str]:
        """Run chat with tool calling and return streaming response"""
        
        logger.debug("🚀 Starting run_chat")
        logger.debug(f"📝 Input messages: {len(messages)}")
        logger.debug(f"⚙️  Constraints: {constraints}")
        logger.debug(f"📍 User location: {user_location}")
        
        # Prepare messages with system prompt
        chat_messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ] + messages
        
        logger.debug(f"💭 System prompt length: {len(SYSTEM_PROMPT)}")

        # Add context about constraints and location if available
        if constraints or user_location:
            context = "User context: "
            if constraints:
                context += f"Constraints: {json.dumps(constraints)}. "
            if user_location:
                context += f"Location: {json.dumps(user_location)}."
            chat_messages.append({"role": "system", "content": context})
            logger.debug(f"📋 Added context: {context}")

        try:
            # Start the conversation with tools
            logger.debug("🤖 Making OpenAI API call with tools")
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=chat_messages,
                tools=self.tools,
                tool_choice="auto",
                stream=False  # We'll handle streaming manually
            )
            
            logger.debug(f"✅ OpenAI response received. Finish reason: {response.choices[0].finish_reason}")

            # Check if tools were called
            if response.choices[0].message.tool_calls:
                logger.debug(f"🔧 Tool calls detected: {len(response.choices[0].message.tool_calls)}")
                # Process tool calls
                chat_messages.append(response.choices[0].message)
                
                for i, tool_call in enumerate(response.choices[0].message.tool_calls):
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"🔧 Calling tool {i+1}/{len(response.choices[0].message.tool_calls)}: {function_name} with args: {function_args}")
                    
                    # Convert string parameters to proper types for vector search
                    if function_name == "search_date_ideas":
                        # Convert numeric parameters from strings to integers
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
                    
                    # Execute the appropriate function
                    if function_name == "search_date_ideas":
                        logger.debug("🔍 Executing vector search")
                        tool_result = await vector_search_func(**function_args)
                        logger.debug(f"📊 Vector search result: {len(tool_result.get('items', []))} items")
                    elif function_name == "web_search":
                        logger.debug("🌐 Executing web search")
                        tool_result = await web_search_func(**function_args)
                        logger.debug(f"📊 Web search result: {len(tool_result.get('items', []))} items")
                    else:
                        logger.error(f"❌ Unknown function: {function_name}")
                        tool_result = {"error": f"Unknown function: {function_name}"}
                    
                    # Add tool result to messages
                    tool_message = {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(tool_result)
                    }
                    chat_messages.append(tool_message)
                    logger.debug(f"📤 Added tool result to chat messages: {len(tool_message['content'])} chars")

                # Get final response after tool execution
                logger.debug("🤖 Making final OpenAI API call with tool results")
                final_response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=chat_messages,
                    stream=True
                )
                
                # Stream the final response
                for chunk in final_response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            else:
                # No tools called, just stream the response
                final_response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=chat_messages,
                    stream=True
                )
                
                for chunk in final_response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Error in LLM chat: {e}")
            yield f"I encountered an error while processing your request: {str(e)}"

    def parse_structured_answer(self, content: str) -> Optional[Dict]:
        """Extract structured answer from the LLM response"""
        try:
            # First try to find explicit JSON in the response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                logger.debug(f"🔍 Found JSON in response: {json_match.group()[:100]}...")
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
