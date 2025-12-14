"""
Advanced Reasoning Agent for Enhanced LLM Engine
Implements Plan-Execute-Reflect patterns for intelligent tool orchestration
"""

import logging
from typing import Dict, List, Any, Optional, AsyncIterator
import json
import asyncio

logger = logging.getLogger(__name__)

class ReasoningAgent:
    """
    Advanced reasoning agent that implements plan-execute-reflect patterns
    for more intelligent tool usage and response generation
    """
    
    def __init__(self, llm_client, tools_manager, vector_search_func=None, web_search_func=None):
        self.llm_client = llm_client
        self.tools_manager = tools_manager
        self.vector_search_func = vector_search_func
        self.web_search_func = web_search_func
        logger.debug("🧠 ReasoningAgent initialized")
    
    async def plan_execute_reflect(
        self, 
        query: str, 
        constraints: Optional[Dict] = None,
        user_location: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        """
        Main reasoning loop: Plan → Execute → Reflect
        """
        logger.info("🧠 Starting Plan-Execute-Reflect reasoning cycle")
        
        try:
            # PHASE 1: PLANNING
            yield "🧠 **Analyzing your request and creating a comprehensive search strategy...**\n\n"
            
            plan = await self.tools_manager.create_execution_plan(
                query=query,
                constraints=constraints,
                user_location=user_location
            )
            
            yield f"📋 **Search Strategy**: {plan['strategy'].title()} approach using {len(plan['primary_tools'])} specialized tools\n\n"
            
            # PHASE 2: EXECUTION
            yield "🚀 **Executing comprehensive search across multiple data sources...**\n\n"
            
            execution_results = await self.tools_manager.execute_plan(
                plan=plan,
                query=query,
                constraints=constraints,
                user_location=user_location
            )
            
            # Report execution progress
            summary = execution_results["execution_summary"]
            yield f"✅ **Search Complete**: {summary['successful_tools']}/{summary['total_tools_executed']} tools succeeded, found {summary['total_items_found']} options from {len(summary['sources_used'])} sources\n\n"
            
            # PHASE 3: REFLECTION & SYNTHESIS
            yield "🤔 **Analyzing and synthesizing results to provide the best recommendations...**\n\n"
            
            # Use LLM to synthesize results
            synthesis_prompt = self._create_synthesis_prompt(
                query=query,
                execution_results=execution_results,
                constraints=constraints
            )
            
            # Stream the final synthesized response
            async for chunk in self._stream_synthesis(synthesis_prompt):
                yield chunk
                
        except Exception as e:
            logger.error(f"❌ Error in plan-execute-reflect cycle: {e}")
            yield f"❌ **Error during reasoning**: {str(e)}\n\n"
            yield "🔄 **Falling back to direct response generation...**\n\n"
            
            # Fallback to simple response
            fallback_prompt = f"User query: {query}\n\nPlease provide a helpful response about date ideas and activities."
            async for chunk in self._stream_synthesis(fallback_prompt):
                yield chunk
    
    def _create_synthesis_prompt(
        self, 
        query: str, 
        execution_results: Dict[str, Any], 
        constraints: Optional[Dict] = None
    ) -> str:
        """Create a comprehensive prompt for result synthesis"""
        
        # Aggregate all results
        all_items = execution_results.get("aggregated_items", [])
        tool_results = execution_results.get("tool_results", {})
        sources_used = execution_results.get("sources_used", set())
        
        # Create detailed context for the LLM
        synthesis_prompt = f"""You are Date Planner AI. Based on comprehensive multi-source research, provide an enthusiastic and detailed response.

USER QUERY: {query}

CONSTRAINTS: {json.dumps(constraints) if constraints else "None"}

COMPREHENSIVE SEARCH RESULTS:
Total items found: {len(all_items)}
Data sources used: {', '.join(sources_used)}
Tools executed: {len(tool_results)}

DETAILED RESULTS BY SOURCE:

"""
        
        # Add results from each tool
        successful_sources = []
        for tool_name, result in tool_results.items():
            if result.get("success", True) and result.get("items"):
                successful_sources.append(tool_name)
                synthesis_prompt += f"\n=== {tool_name.upper()} RESULTS ===\n"
                synthesis_prompt += f"Found {len(result['items'])} items:\n"
                
                for i, item in enumerate(result["items"][:5]):  # Limit to top 5 per source
                    synthesis_prompt += f"\n{i+1}. {item.get('title', 'Untitled')}\n"
                    if item.get('address'):
                        synthesis_prompt += f"   Address: {item['address']}\n"
                    if item.get('rating'):
                        synthesis_prompt += f"   Rating: {item['rating']}/5\n"
                    if item.get('price'):
                        synthesis_prompt += f"   Price: {item['price']}\n"
                    if item.get('description'):
                        synthesis_prompt += f"   Description: {item['description'][:200]}...\n"
                    if item.get('website') or item.get('url'):
                        synthesis_prompt += f"   Website: {item.get('website') or item.get('url')}\n"
            else:
                synthesis_prompt += f"\n=== {tool_name.upper()} ===\n"
                synthesis_prompt += f"No results or error: {result.get('error', 'No items found')}\n"
        
        # Add explicit requirement to use all successful sources
        if successful_sources:
            synthesis_prompt += f"\n🎯 MANDATORY SOURCE USAGE:\nYou MUST include results from ALL these successful sources in your response: {', '.join(successful_sources)}\nDo not ignore any source - each provides valuable unique information.\n"
        
        synthesis_prompt += """

RESPONSE REQUIREMENTS:
1. Be enthusiastic and positive - "I found fantastic options!"
2. NEVER say "no results" or "limited options" - present everything as valuable discoveries
3. Provide specific venue details (address, phone, website, hours when available)
4. Organize by categories or themes
5. Include practical logistics information
6. Must provide structured JSON followed by conversational response
7. Use all available data comprehensively
8. MANDATORY SOURCE DIVERSITY: Must include at least one result from EACH successful source (eventbrite, enhanced_web_search, google_places)
9. When multiple sources have the same venue, combine their information
10. Present web search and eventbrite results as "Additional Resources" or "Events" sections

REQUIRED JSON FORMAT:
```json
{
  "summary": "I found fantastic [activity] options in [city]!",
  "options": [
    {
      "title": "Venue Name",
      "categories": ["relevant", "tags"],
      "price": "$$ or specific pricing",
      "duration_min": 120,
      "why_it_fits": "Perfect for [request] because...",
      "logistics": "Address: X, Phone: Y, Hours: Z, Website: url",
      "website": "https://website.com",
      "source": "google_places|vector_store|web|eventbrite|mixed",
      "entity_references": {
        "primary_entity": {"id": "venue_id", "type": "venues", "title": "Name", "url": "/api/venues/id"}
      },
      "citations": [{"url": "https://source.com", "title": "Source"}]
    }
  ]
}
```

Provide the JSON followed by an enthusiastic conversational response with detailed recommendations!
"""
        
        return synthesis_prompt
    
    async def _stream_synthesis(self, prompt: str) -> AsyncIterator[str]:
        """Stream the synthesis response from the LLM"""
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",  # Using cheaper model (~90% cost reduction)
                messages=[
                    {"role": "system", "content": "You are an enthusiastic Date Planner AI that provides comprehensive, positive recommendations."},
                    {"role": "user", "content": prompt}
                ],
                stream=True,
                temperature=0.7
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"❌ Error streaming synthesis: {e}")
            yield f"I found some great options for you based on my comprehensive search! "
            yield f"Let me share what I discovered across multiple sources.\n\n"
    
    async def reflect_on_results(self, results: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Reflect on the quality and completeness of results
        """
        reflection = {
            "completeness_score": 0.0,
            "quality_score": 0.0,
            "coverage_analysis": {},
            "improvement_suggestions": [],
            "missing_aspects": []
        }
        
        total_items = len(results.get("aggregated_items", []))
        sources_used = len(results.get("sources_used", set()))
        successful_tools = results.get("execution_summary", {}).get("successful_tools", 0)
        
        # Calculate completeness score
        if total_items >= 10:
            reflection["completeness_score"] = 1.0
        elif total_items >= 5:
            reflection["completeness_score"] = 0.8
        elif total_items >= 1:
            reflection["completeness_score"] = 0.6
        else:
            reflection["completeness_score"] = 0.0
        
        # Calculate quality score based on source diversity
        if sources_used >= 3:
            reflection["quality_score"] = 1.0
        elif sources_used >= 2:
            reflection["quality_score"] = 0.8
        else:
            reflection["quality_score"] = 0.6
        
        # Analyze coverage
        sources_used = results.get("sources_used", set())
        reflection["coverage_analysis"] = {
            "has_local_venues": "google_places" in sources_used,
            "has_events": "eventbrite" in sources_used,
            "has_curated_content": "vector_store" in sources_used,
            "has_web_research": "web" in sources_used
        }
        
        # Suggest improvements
        if total_items < 5:
            reflection["improvement_suggestions"].append("Consider broader search terms")
        if sources_used < 3:
            reflection["improvement_suggestions"].append("Try additional data sources")
        
        logger.info(f"🤔 Reflection complete: Completeness={reflection['completeness_score']:.1f}, Quality={reflection['quality_score']:.1f}")
        
        return reflection

    async def adaptive_tool_selection(self, query: str, previous_results: Optional[Dict] = None) -> List[str]:
        """
        Dynamically select tools based on query analysis and previous results
        """
        base_analysis = self.tools_manager.analyze_query_intent(query)
        recommended_tools = base_analysis["recommended_tools"].copy()
        
        # Adapt based on previous results
        if previous_results:
            reflection = await self.reflect_on_results(previous_results, query)
            
            # Add more tools if results were incomplete
            if reflection["completeness_score"] < 0.7:
                additional_tools = ["web_scrape_venue_info", "find_nearby_venues"]
                for tool in additional_tools:
                    if tool not in recommended_tools:
                        recommended_tools.append(tool)
            
            # Focus on missing aspects
            coverage = reflection["coverage_analysis"]
            if not coverage.get("has_events") and "eventbrite_search" not in recommended_tools:
                recommended_tools.insert(0, "eventbrite_search")
            if not coverage.get("has_local_venues") and "google_places_search" not in recommended_tools:
                recommended_tools.insert(0, "google_places_search")
        
        logger.info(f"🎯 Adaptive tool selection: {len(recommended_tools)} tools selected")
        return recommended_tools[:6]  # Limit to 6 tools max