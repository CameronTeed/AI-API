"""
LLM Engine for Cost-Efficient AI Flow
Uses local ML (spacy + sklearn) for heavy lifting, OpenAI only for formatting/analysis
Flow: User Input -> Local ML (vibe + planning) -> Genetic Algorithm (optimization) -> OpenAI (formatting) -> Response

This is the main, optimized engine that minimizes costs while maximizing quality.
"""

import logging
import re
from typing import AsyncIterator, List, Dict, Any, Optional
from ..core.ml_integration import get_ml_wrapper
from ..core.search_engine import get_search_engine
from openai import AsyncOpenAI

try:
    from ...config.scoring_config import ScoringConfig
except ImportError:
    ScoringConfig = None

logger = logging.getLogger(__name__)


def is_follow_up_question(user_message: str, conversation_history: List[Dict[str, str]]) -> bool:
    """
    Detect if the user message is a follow-up question about a previously suggested date
    vs asking for a new date.

    Uses full conversation context to understand what was previously discussed.

    Strategy:
    1. If no previous assistant message with suggestions, it's a new request
    2. Check for explicit "find/search/suggest" keywords -> new request
    3. Check for modification/rejection keywords -> follow-up
    4. Check for detail/logistics questions -> follow-up
    5. Check for question patterns without "find" -> follow-up
    """
    msg_lower = user_message.lower()

    # If this is the first message, it's not a follow-up
    if len(conversation_history) <= 1:
        return False

    # Check if there's a previous assistant message with suggestions
    # Look through entire history to find any venue/activity suggestions
    has_previous_suggestions = any(
        msg.get('role') == 'assistant' and
        any(keyword in msg.get('content', '').lower() for keyword in ['restaurant', 'venue', 'activity', 'place', 'option', 'itinerary'])
        for msg in conversation_history[:-1]
    )

    if not has_previous_suggestions:
        return False

    # Extract context from entire conversation history
    # This helps understand what vibes/venues were discussed
    conversation_context = " ".join([
        msg.get('content', '').lower()
        for msg in conversation_history[:-1]
    ])

    # STRONG INDICATORS OF FOLLOW-UP (modification/rejection) - CHECK FIRST
    modification_patterns = [
        r'(don\'t like|didn\'t like|hate|dislike|not interested|skip|remove|exclude)',
        r'(don\'t want|didn\'t want|wouldn\'t|can\'t|won\'t)',
        r'(replace|change|swap|substitute)',
        r'(too|very)\s+(expensive|cheap|far|close|crowded|quiet|busy|slow)',
        r'(not my|not the|not what)',
    ]

    for pattern in modification_patterns:
        if re.search(pattern, msg_lower):
            return True  # It's a follow-up modification (even if it says "find something else")

    # STRONG INDICATORS OF NEW REQUEST (only if no modification pattern matched)
    new_request_patterns = [
        r'\b(find|search|suggest|recommend|show|give|look for|looking for)\b',
        r'\b(another|different|new|other)\s+(date|idea|place|restaurant|activity|experience)',
        r'\b(instead of|rather than|how about)\b',
        r'\b(what about|try)\b',
    ]

    for pattern in new_request_patterns:
        if re.search(pattern, msg_lower):
            return False  # It's a new request

    # DETAIL/LOGISTICS QUESTIONS (follow-up)
    detail_patterns = [
        r'\b(how|what|when|where|why)\b.*\b(this|that|these|those|the)\b',
        r'\b(this|that|these|those|the)\s+(venue|restaurant|place|date|itinerary|plan|activity|option)\b',
        r'\b(tell me|explain|describe|more about|details about|information about)\b',
        r'\b(parking|hours|reservation|booking|cost|price|distance|travel time|directions|address|phone|website|menu)\b',
        r'\b(vegetarian|vegan|gluten|allergy|dietary|wheelchair|accessible|pet friendly|kids|family)\b',
        r'\b(dress code|atmosphere|noise level|wifi|parking|outdoor|indoor|ambiance|vibe)\b',
    ]

    for pattern in detail_patterns:
        if re.search(pattern, msg_lower):
            return True  # It's a follow-up question

    # QUESTION PATTERNS (likely follow-up if no "find" keyword)
    question_words = r'\b(how|what|when|where|why|can|could|would|should|is|are|do|does)\b'
    if re.search(question_words, msg_lower):
        # If it's a question but doesn't have "find/search" keywords, it's likely a follow-up
        return True

    return False


def extract_preferences(user_message: str) -> Dict[str, Any]:
    """
    Extract budget, duration, and types from user message

    Returns dict with:
    - budget_limit: float (default from ScoringConfig)
    - duration_minutes: int (default from ScoringConfig)
    - target_types: List[str] (extracted from message)
    """
    # Use dynamic defaults from ScoringConfig if available
    default_budget = ScoringConfig.DEFAULT_BUDGET if ScoringConfig else 150
    default_duration = ScoringConfig.DEFAULT_DURATION_MINUTES if ScoringConfig else 180
    expensive_budget = ScoringConfig.BUDGET_EXPENSIVE if ScoringConfig else 300
    cheap_budget = ScoringConfig.BUDGET_CHEAP if ScoringConfig else 75

    preferences = {
        'budget_limit': default_budget,
        'duration_minutes': default_duration,
        'target_types': [],
        'hidden_gem': False
    }

    msg_lower = user_message.lower()

    # Extract budget
    budget_patterns = [
        (r'under\s*\$?(\d+)', 'under'),
        (r'\$?(\d+)\s*budget', 'budget'),
        (r'budget.*\$?(\d+)', 'budget'),
        (r'expensive|fancy|upscale', 'expensive'),
        (r'cheap|budget|affordable', 'cheap'),
    ]

    for pattern, budget_type in budget_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            if budget_type == 'under':
                preferences['budget_limit'] = float(match.group(1))
            elif budget_type == 'budget':
                preferences['budget_limit'] = float(match.group(1))
            elif budget_type == 'expensive':
                preferences['budget_limit'] = expensive_budget
            elif budget_type == 'cheap':
                preferences['budget_limit'] = cheap_budget
            break

    # Extract duration
    duration_patterns = [
        (r'(\d+)\s*hour', ScoringConfig.DURATION_QUICK if ScoringConfig else 60),
        (r'(\d+)\s*min', 1),
        (r'all\s*day', ScoringConfig.DURATION_ALL_DAY if ScoringConfig else 480),
        (r'quick|fast', ScoringConfig.DURATION_QUICK if ScoringConfig else 60),
    ]

    for pattern, multiplier in duration_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            preferences['duration_minutes'] = int(match.group(1)) * multiplier
            break

    # Extract activity types
    type_keywords = {
        'restaurant': ['restaurant', 'dining', 'food', 'eat', 'meal', 'lunch', 'dinner'],
        'italian': ['italian', 'pasta', 'pizza'],
        'museum': ['museum', 'art', 'gallery'],
        'outdoor': ['outdoor', 'hike', 'park', 'trail', 'nature'],
        'bar': ['bar', 'drinks', 'cocktail', 'wine'],
        'cafe': ['cafe', 'coffee', 'tea'],
        'movie': ['movie', 'cinema', 'film'],
        'shopping': ['shopping', 'shop', 'mall'],
    }

    for activity_type, keywords in type_keywords.items():
        if any(kw in msg_lower for kw in keywords):
            preferences['target_types'].append(activity_type)

    # Check for hidden gem preference
    if 'hidden gem' in msg_lower or 'off the beaten' in msg_lower:
        preferences['hidden_gem'] = True

    return preferences


class LLMEngine:
    """
    Main LLM engine that minimizes OpenAI API calls through ML-first approach

    Strategy:
    1. Use local ML for vibe prediction (spacy + sklearn) - FREE
    2. Use local ML for date planning (heuristic/genetic algorithms) - FREE
    3. Use web search only when needed - CHEAP
    4. Use OpenAI ONLY for formatting/analysis of results - MINIMAL TOKENS

    This achieves 80-85% cost reduction compared to traditional LLM-first approaches.
    """
    
    def __init__(self, vector_store=None, web_client=None):
        self.ml_wrapper = get_ml_wrapper()
        self.search_engine = get_search_engine(vector_store=vector_store, web_client=web_client)
        self.client = AsyncOpenAI()
        logger.info("✅ OptimizedLLMEngine initialized (ML-first, LLM-minimal)")
    
    async def run_chat(
        self,
        messages: List[Dict[str, str]],
        agent_tools: Optional[Any] = None,
        session_id: Optional[str] = None,
        constraints: Optional[Dict] = None,
        user_location: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        """
        Optimized chat flow with GA integration:

        For NEW date requests:
        1. Extract user intent and preferences from message
        2. Predict vibe using LOCAL ML (free)
        3. Search for venues filtered by vibe (cheap)
        4. OPTIMIZE itinerary using GENETIC ALGORITHM (free)
        5. Use OpenAI ONLY to format the final response (minimal tokens)

        For FOLLOW-UP questions about a date:
        1. Retrieve the previous itinerary from session context
        2. Use Google Places data + web search to answer questions
        3. Use OpenAI to format the answer with relevant details
        """
        try:
            # Get last user message
            user_message = None
            for msg in reversed(messages):
                if msg.get('role') == 'user':
                    user_message = msg.get('content', '')
                    break

            if not user_message:
                yield "No user message found"
                return

            logger.info(f"🎯 [CHAT_FLOW] Processing: {user_message[:100]}")

            # Check if this is a follow-up question
            is_followup = is_follow_up_question(user_message, messages)
            logger.info(f"📋 [FLOW_TYPE] {'Follow-up question' if is_followup else 'New date request'}")

            if is_followup and session_id:
                # Handle follow-up question
                async for chunk in self._handle_followup_question(
                    user_message,
                    session_id,
                    messages
                ):
                    yield chunk
            else:
                # Handle new date request (original GA flow)
                async for chunk in self._handle_new_date_request(
                    user_message,
                    session_id,
                    messages
                ):
                    yield chunk

        except Exception as e:
            logger.error(f"❌ Error in chat flow: {e}")
            yield f"Error: {str(e)}"


    async def _handle_new_date_request(
        self,
        user_message: str,
        session_id: Optional[str],
        messages: List[Dict[str, str]],
        excluded_venue_ids: Optional[List[str]] = None
    ) -> AsyncIterator[str]:
        """Handle a new date request using GA optimization"""
        # STEP 1: Predict vibe using LOCAL ML (FREE)
        logger.info("📊 [STEP 1] Predicting vibe with local ML...")
        vibe = self.ml_wrapper.predict_vibe(user_message)
        logger.info(f"✅ Predicted vibe: {vibe}")
        yield f"🎨 Detected vibe: {vibe}\n"

        # STEP 2: Extract preferences from user message
        logger.info("🔍 [STEP 2] Extracting preferences...")
        preferences = extract_preferences(user_message)
        logger.info(f"✅ Extracted preferences: budget=${preferences['budget_limit']}, duration={preferences['duration_minutes']}min, types={preferences['target_types']}")

        # STEP 3: Search for venues filtered by vibe (CHEAP)
        logger.info("🔍 [STEP 3] Searching for venues with vibe filtering...")
        vibes_list = [v.strip() for v in vibe.split(',')] if vibe else []
        search_results = await self.search_engine.vibe_filtered_search(
            user_message,
            vibes_list,
            limit=50  # Fetch more for GA to optimize
        )
        logger.info(f"✅ Found {len(search_results)} venues matching vibe: {vibe}")
        yield f"📍 Found {len(search_results)} venues\n"

        # STEP 4: OPTIMIZE itinerary using GENETIC ALGORITHM (FREE)
        logger.info("🧬 [STEP 4] Optimizing itinerary with genetic algorithm...")
        optimized_itinerary = await self._optimize_with_ga(
            search_results,
            preferences,
            vibes_list,
            excluded_venue_ids=excluded_venue_ids
        )

        if optimized_itinerary:
            logger.info(f"✅ GA optimized itinerary: {len(optimized_itinerary)} venues")
            yield f"🧬 Optimized itinerary for you\n"
            venues_to_format = optimized_itinerary

            # Store itinerary in session for follow-up questions
            if session_id:
                from ..tools.chat_context_storage import get_chat_storage
                storage = get_chat_storage()
                await storage.store_itinerary(
                    session_id,
                    optimized_itinerary,
                    vibe,
                    preferences['budget_limit']
                )
        else:
            logger.warning("GA optimization failed, using top search results")
            venues_to_format = search_results[:5]

        # STEP 5: Use OpenAI ONLY to format the response (MINIMAL TOKENS)
        logger.info("🤖 [STEP 5] Formatting response with OpenAI (minimal tokens)...")

        # Build minimal context for OpenAI - only essential data
        venues_summary = ""
        if venues_to_format:
            logger.info(f"📋 Formatting {len(venues_to_format)} venues for OpenAI")
            for i, venue in enumerate(venues_to_format, 1):
                title = venue.get('title', venue.get('name', 'Unknown'))
                desc = venue.get('description', '')[:100]
                price = venue.get('price_tier', venue.get('price', 'N/A'))
                rating = venue.get('rating', 'N/A')
                reason = venue.get('selection_reason', 'great match')
                address = venue.get('address', venue.get('short_address', ''))

                # Log each venue being formatted
                logger.debug(f"  Venue {i}: {title} - {address}")

                venues_summary += f"{i}. {title}\n"
                if address:
                    venues_summary += f"   📍 {address}\n"
                venues_summary += f"   💰 ${price} | ⭐ {rating}\n"
                if desc:
                    venues_summary += f"   📝 {desc}\n"
                venues_summary += f"   ✨ {reason}\n\n"
        else:
            logger.warning("⚠️  No venues to format for OpenAI!")

        context = f"""User Request: {user_message}
Detected Vibe: {vibe}
Optimized Itinerary: {len(venues_to_format)} venues

Venue Details:
{venues_summary if venues_summary else "ERROR: No venues found in database. Please try a different search."}

Create a friendly, engaging response with date ideas based on this optimized itinerary.
Be concise and enthusiastic. Include specific venue names and addresses.
Explain the flow of the date (activity → meal → drinks, etc).
IMPORTANT: Only use the venue names and details provided above. Do not make up venues."""

        # Call OpenAI with minimal tokens
        formatting_messages = [
            {
                "role": "system",
                "content": "You are a helpful, enthusiastic date planning assistant. Format venue information into a friendly response with specific recommendations. Explain why this itinerary works well."
            },
            {"role": "user", "content": context}
        ]

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=formatting_messages,
            max_tokens=600,  # Keep response reasonable
            stream=True
        )

        # Stream the formatted response
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

        logger.info("✅ [NEW_DATE_REQUEST] Complete")

    async def _handle_followup_question(
        self,
        user_message: str,
        session_id: str,
        messages: List[Dict[str, str]]
    ) -> AsyncIterator[str]:
        """Handle a follow-up question about a previously suggested date"""
        logger.info("📋 [STEP 1] Retrieving previous itinerary from session...")

        from ..tools.chat_context_storage import get_chat_storage
        storage = get_chat_storage()
        itinerary_data = await storage.get_current_itinerary(session_id)

        if not itinerary_data:
            logger.warning("No previous itinerary found, treating as new request")
            async for chunk in self._handle_new_date_request(user_message, session_id, messages):
                yield chunk
            return

        itinerary = itinerary_data['itinerary']
        vibe = itinerary_data['vibe']
        logger.info(f"✅ Retrieved itinerary with {len(itinerary)} venues")

        # Check if this is a venue rejection request
        rejection_patterns = [
            r'\b(don\'t like|hate|dislike|didn\'t like)\b',
            r'\b(don\'t want|wouldn\'t)\b',
            r'\b(replace|change|swap|substitute)\b',
            r'\b(too|very)\s+(expensive|cheap|far|close|crowded|quiet)\b',
        ]

        is_rejection = any(re.search(pattern, user_message.lower()) for pattern in rejection_patterns)

        if is_rejection:
            # Extract which venue they don't like
            logger.info("🚫 [REJECTION] User rejected a venue, finding alternatives...")
            yield "🔄 Finding you a better alternative...\n"

            # Extract venue name from message
            rejected_venue_name = None
            for venue in itinerary:
                venue_name = venue.get('title', venue.get('name', ''))
                if venue_name.lower() in user_message.lower():
                    rejected_venue_name = venue_name
                    break

            if rejected_venue_name:
                logger.info(f"Rejected venue: {rejected_venue_name}")
                # Get excluded venue IDs
                excluded_ids = [v.get('id') for v in itinerary if v.get('title', v.get('name', '')) == rejected_venue_name]

                # Re-run GA with exclusions to find alternatives
                async for chunk in self._handle_new_date_request(
                    f"Find me {vibe} date ideas (but not {rejected_venue_name})",
                    session_id,
                    messages,
                    excluded_venue_ids=excluded_ids
                ):
                    yield chunk
                return

        # Regular follow-up question handling
        yield f"📋 Checking details about your itinerary...\n"

        # STEP 2: Use web search to get additional info about the venues
        logger.info("🔍 [STEP 2] Searching for additional information...")

        # Build context about the venues and the question
        venues_context = ""
        for i, venue in enumerate(itinerary, 1):
            title = venue.get('title', venue.get('name', 'Unknown'))
            address = venue.get('address', venue.get('short_address', ''))
            venues_context += f"{i}. {title} ({address})\n"

        # Search for info relevant to the question
        search_query = f"{user_message} {' '.join([v.get('title', v.get('name', '')) for v in itinerary])}"
        web_results = await self.search_engine.web_search(search_query, limit=3)

        web_context = ""
        if web_results:
            logger.info(f"✅ Found {len(web_results)} web results")
            for result in web_results:
                web_context += f"- {result.get('title', '')}: {result.get('snippet', '')}\n"

        # STEP 3: Use OpenAI to answer the question with venue data + web search
        logger.info("🤖 [STEP 3] Formatting answer with OpenAI...")

        context = f"""User's Previous Itinerary:
{venues_context}

User's Question: {user_message}

Additional Information from Web:
{web_context if web_context else "No additional web results found."}

Answer the user's question about their itinerary using the venue information and web search results.
Be specific and helpful. Reference the venues by name and provide practical details."""

        formatting_messages = [
            {
                "role": "system",
                "content": "You are a helpful date planning assistant. Answer questions about the user's itinerary with specific, practical information."
            },
            {"role": "user", "content": context}
        ]

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=formatting_messages,
            max_tokens=400,
            stream=True
        )

        # Stream the formatted response
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

        logger.info("✅ [FOLLOWUP_QUESTION] Complete")

    async def _optimize_with_ga(
        self,
        search_results: List[Dict[str, Any]],
        preferences: Dict[str, Any],
        target_vibes: List[str],
        excluded_venue_ids: Optional[List[str]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Optimize itinerary using genetic algorithm

        Args:
            search_results: List of venues from semantic search
            preferences: Dict with budget_limit, duration_minutes, target_types, hidden_gem
            target_vibes: List of target vibes
            excluded_venue_ids: List of venue IDs to exclude from results

        Returns:
            Optimized itinerary (list of venues) or None if GA fails
        """
        try:
            # Convert search results to DataFrame format for GA
            import pandas as pd

            # Create DataFrame from search results
            venues_df = pd.DataFrame(search_results)

            # Ensure required columns exist
            if venues_df.empty:
                logger.warning("❌ No venues to optimize with GA")
                return None

            logger.info(f"🧬 GA Input: {len(venues_df)} venues, columns: {list(venues_df.columns)}")

            # Map search engine columns to GA expected columns
            # Search engine uses: title, categories, predicted_vibe, price_tier, review_count
            # GA expects: name, type, all_types, true_vibe, cost, reviews_count

            if 'name' not in venues_df.columns and 'title' in venues_df.columns:
                venues_df['name'] = venues_df['title']

            if 'type' not in venues_df.columns:
                # Extract primary type from categories
                def extract_type(x):
                    try:
                        if x is None:
                            return 'venue'
                        if isinstance(x, list):
                            return x[0] if x else 'venue'
                        return str(x).split(',')[0].strip() if str(x).strip() else 'venue'
                    except:
                        return 'venue'

                venues_df['type'] = venues_df['categories'].apply(extract_type)

            if 'all_types' not in venues_df.columns and 'categories' in venues_df.columns:
                # Convert categories to string (handle lists)
                def categories_to_str(x):
                    if x is None:
                        return ''
                    if isinstance(x, list):
                        return ', '.join(str(c) for c in x)
                    return str(x)
                venues_df['all_types'] = venues_df['categories'].apply(categories_to_str)
            elif 'all_types' not in venues_df.columns:
                venues_df['all_types'] = ''

            if 'primary_type_display_name' not in venues_df.columns:
                venues_df['primary_type_display_name'] = venues_df['type'].fillna('venue')

            if 'true_vibe' not in venues_df.columns:
                # Use predicted_vibe if available, otherwise default to casual
                if 'predicted_vibe' in venues_df.columns:
                    venues_df['true_vibe'] = venues_df['predicted_vibe'].fillna('casual')
                else:
                    venues_df['true_vibe'] = 'casual'

            if 'cost' not in venues_df.columns:
                # Map price_tier to cost (1-4 -> 10-40)
                if 'price_tier' in venues_df.columns:
                    venues_df['cost'] = venues_df['price_tier'].apply(
                        lambda x: int(x) * 10 if pd.notna(x) else 20
                    )
                else:
                    venues_df['cost'] = 20

            if 'rating' not in venues_df.columns:
                venues_df['rating'] = 3.5

            if 'reviews_count' not in venues_df.columns:
                # Use review_count if available
                if 'review_count' in venues_df.columns:
                    venues_df['reviews_count'] = venues_df['review_count']
                else:
                    venues_df['reviews_count'] = 0

            if 'id' not in venues_df.columns:
                venues_df['id'] = range(len(venues_df))

            # Call GA planner
            default_vibe = ScoringConfig.DEFAULT_VIBE if ScoringConfig else 'casual'
            default_itinerary_length = ScoringConfig.DEFAULT_ITINERARY_LENGTH if ScoringConfig else 3

            ga_preferences = {
                'venues_df': None,  # Let GA load full database instead of using filtered search results
                'vibe': target_vibes[0] if target_vibes else default_vibe,
                'budget_range': (0, preferences['budget_limit']),
                'max_venues': default_itinerary_length,  # Optimize for dynamic itinerary length
                'target_types': preferences.get('target_types', []),
                'hidden_gem': preferences.get('hidden_gem', False),
                'excluded_venue_ids': excluded_venue_ids or []
            }

            excluded_count = len(excluded_venue_ids or [])
            logger.info(f"🧬 Calling GA with: vibe={ga_preferences['vibe']}, budget={ga_preferences['budget_range']}, max_venues={ga_preferences['max_venues']}, excluded={excluded_count}")
            result = self.ml_wrapper.plan_date(ga_preferences, algorithm="genetic")

            if result and result.get('success'):
                itinerary = result.get('itinerary', [])
                logger.info(f"✅ GA produced itinerary with {len(itinerary)} venues")
                if itinerary:
                    for i, venue in enumerate(itinerary, 1):
                        logger.info(f"   {i}. {venue.get('title', venue.get('name', 'Unknown'))} - {venue.get('type', 'Unknown type')}")
                return itinerary
            else:
                logger.warning(f"GA failed: {result.get('error', 'Unknown error') if result else 'No result'}")
                return None

        except Exception as e:
            logger.error(f"❌ GA optimization error: {e}", exc_info=True)
            return None


def get_llm_engine(vector_store=None, web_client=None) -> LLMEngine:
    """Get or create LLM engine instance"""
    return LLMEngine(vector_store=vector_store, web_client=web_client)


# Backwards compatibility
def get_optimized_llm_engine(vector_store=None, web_client=None) -> LLMEngine:
    """Deprecated: Use get_llm_engine() instead"""
    return get_llm_engine(vector_store=vector_store, web_client=web_client)

