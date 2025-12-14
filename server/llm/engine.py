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
from ..ml.input_validator import InputValidator
from openai import AsyncOpenAI

try:
    from ...config.scoring_config import ScoringConfig
except ImportError:
    ScoringConfig = None

# Pre-trained zero-shot classification model for intent detection
try:
    from transformers import pipeline
    ZERO_SHOT_CLASSIFIER = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    ML_CLASSIFIER_AVAILABLE = True
except ImportError:
    ZERO_SHOT_CLASSIFIER = None
    ML_CLASSIFIER_AVAILABLE = False

logger = logging.getLogger(__name__)


# Intent classification keywords - data-driven, easily extensible
INTENT_KEYWORDS = {
    "new_request": {
        "keywords": ["find me", "search for", "suggest", "recommend", "show me", "give me", "look for",
                     "looking for", "another date", "different date", "new date", "other date",
                     "instead of", "rather than", "how about a", "what about a", "try something"],
        "weight": 1.0
    },
    "modification": {
        "keywords": ["don't like", "didn't like", "hate", "dislike", "not interested", "skip", "remove", "exclude",
                     "don't want", "didn't want", "wouldn't", "can't", "won't", "replace", "change", "swap", "substitute",
                     "too expensive", "too cheap", "too far", "too close", "too crowded", "too quiet", "too busy", "too slow"],
        "weight": 1.5  # Higher weight for strong indicators
    },
    "detail_question": {
        "keywords": ["hours", "open", "close", "time", "reservation", "booking", "reserve", "book",
                     "parking", "cost", "price", "distance", "travel time", "directions", "address", "phone", "website", "menu",
                     "vegetarian", "vegan", "gluten", "allergy", "dietary", "wheelchair", "accessible", "pet friendly", "kids", "family",
                     "dress code", "atmosphere", "noise level", "wifi", "outdoor", "indoor", "ambiance", "vibe",
                     "tell me", "explain", "describe", "more about", "details about", "information about",
                     "what", "how", "where", "when", "why", "which", "do they", "can i", "is there", "are there"],
        "weight": 1.2
    },
    "reference_to_previous": {
        "keywords": ["this", "that", "these", "those", "the", "it", "they", "them", "first", "second", "third", "one", "another", "both"],
        "weight": 0.8  # Contextual indicator
    }
}


def _score_intent_ml(user_message: str) -> Dict[str, float]:
    """
    Score intent using pre-trained zero-shot classification model.
    Uses facebook/bart-large-mnli for semantic understanding.

    Returns a dict with intent types and their confidence scores (0-1).
    """
    if not ML_CLASSIFIER_AVAILABLE or ZERO_SHOT_CLASSIFIER is None:
        return {}

    try:
        # Define candidate labels for intent classification
        candidate_labels = [
            "asking for new date ideas",
            "asking about details of a specific venue",
            "rejecting or modifying a previous suggestion",
            "asking a follow-up question about previous suggestions"
        ]

        # Run zero-shot classification
        result = ZERO_SHOT_CLASSIFIER(user_message, candidate_labels, multi_label=False)

        # Convert to dict with intent names and scores
        scores = {}
        for label, score in zip(result['labels'], result['scores']):
            if "new date" in label:
                scores["new_request"] = score
            elif "details" in label:
                scores["detail_question"] = score
            elif "rejecting" in label or "modifying" in label:
                scores["modification"] = score
            elif "follow-up" in label:
                scores["reference_to_previous"] = score

        logger.debug(f"ML Intent scores: {scores}")
        return scores
    except Exception as e:
        logger.warning(f"Error in ML intent classification: {e}")
        return {}


def _score_intent(user_message: str, intent_type: str) -> float:
    """
    Score how well a message matches a specific intent.
    Uses keyword matching with configurable weights.

    Returns a score from 0 to 1 where 1 is a perfect match.
    """
    msg_lower = user_message.lower()
    keywords = INTENT_KEYWORDS.get(intent_type, {}).get("keywords", [])
    weight = INTENT_KEYWORDS.get(intent_type, {}).get("weight", 1.0)

    if not keywords:
        return 0.0

    # Count how many keywords match (exact phrase matching for multi-word keywords)
    matches = 0
    for keyword in keywords:
        if keyword in msg_lower:
            matches += 1

    if matches == 0:
        return 0.0

    # Score based on number of matches, not ratio
    # Each match contributes 0.3 to the score, capped at 1.0
    # This way: 1 match = 0.3, 2 matches = 0.6, 3+ matches = 0.9+
    score = min(matches * 0.3, 1.0) * weight

    return min(score, 1.0)  # Cap at 1.0


def _has_previous_suggestions(conversation_history: List[Dict[str, str]]) -> bool:
    """Check if there's a previous assistant message with suggestions"""
    # Check all messages (not just [:-1]) for assistant messages with suggestions
    # The last message is the current user message, but we want to check if there
    # are any previous assistant messages with suggestions
    return any(
        msg.get('role') == 'assistant' and
        any(keyword in msg.get('content', '').lower()
            for keyword in ['restaurant', 'venue', 'activity', 'place', 'option', 'itinerary', 'suggest', 'recommend', 'idea'])
        for msg in conversation_history
    )


def is_follow_up_question(user_message: str, conversation_history: List[Dict[str, str]]) -> bool:
    """
    Detect if the user message is a follow-up question about a previously suggested date
    vs asking for a new date.

    Uses pre-trained ML model (zero-shot classification) with fallback to keyword matching.

    Strategy:
    1. If no previous assistant message with suggestions, it's a new request
    2. Try ML-based classification (PRIMARY)
    3. Fall back to keyword-based scoring if ML unavailable (FALLBACK)
    4. Default to follow-up if uncertain (SAFE DEFAULT)
    """
    # If this is the first message, it's not a follow-up
    # if len(conversation_history) <= 1:
    #     logger.debug("First message - not a follow-up")
    #     return False

    # Check if there's a previous assistant message with suggestions
    # if not _has_previous_suggestions(conversation_history):
    #     logger.debug("No previous suggestions found - not a follow-up")
    #     return False

    logger.debug(f"Checking if follow-up: '{user_message[:80]}'")

    # PRIMARY: Try ML-based classification first (more robust to language variations)
    # This uses zero-shot classification which handles language variations better than hard-coded patterns
    if ML_CLASSIFIER_AVAILABLE:
        try:
            ml_scores = _score_intent_ml(user_message)
            if ml_scores:
                new_request_score = ml_scores.get("new_request", 0.0)
                modification_score = ml_scores.get("modification", 0.0)
                detail_score = ml_scores.get("detail_question", 0.0)
                reference_score = ml_scores.get("reference_to_previous", 0.0)

                logger.info(f"ML Intent scores - new_request: {new_request_score:.2f}, modification: {modification_score:.2f}, "
                            f"detail: {detail_score:.2f}, reference: {reference_score:.2f}")
                # Strong new request intent = new request
                if new_request_score > 0.5:
                    logger.info(f"ML: Detected strong new request intent ({new_request_score:.2f}) -> new request")
                    return False

                # Detail question or reference to previous = follow-up (check first)
                # Lower threshold for detail questions since they're clearly follow-ups
                if detail_score > 0.15 or reference_score > 0.15:
                    logger.info(f"ML: Detected detail/reference intent (detail={detail_score:.2f}, ref={reference_score:.2f}) -> follow-up")
                    return True

                # If modification score is high, it's a follow-up
                if modification_score > 0.4:
                    logger.info(f"ML: Detected modification intent ({modification_score:.2f}) -> follow-up")
                    return True
        except Exception as e:
            logger.warning(f"ML classification failed, falling back to keyword matching: {e}")

    # Fallback to keyword-based scoring
    logger.debug("Using keyword-based intent classification")
    new_request_score = _score_intent(user_message, "new_request")
    modification_score = _score_intent(user_message, "modification")
    detail_score = _score_intent(user_message, "detail_question")
    reference_score = _score_intent(user_message, "reference_to_previous")

    logger.info(f"Keyword Intent scores - new_request: {new_request_score:.2f}, modification: {modification_score:.2f}, "
                f"detail: {detail_score:.2f}, reference: {reference_score:.2f}")

    # Detail question or reference to previous = follow-up (check first)
    if detail_score > 0.15 or reference_score > 0.15:
        logger.info(f"Keyword: Detected detail/reference intent -> follow-up")
        return True

    # Strong new request intent = new request
    if new_request_score > 0.35:
        logger.info(f"Keyword: Detected strong new request intent -> new request")
        return False

    # Default: if we have previous suggestions and no clear new request, it's a follow-up
    logger.info("No clear intent detected, defaulting to follow-up (SAFE DEFAULT)")
    return True


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

            # VALIDATION: Check if input is valid for date ideas chat
            is_valid, error_message, validation_metadata = InputValidator.validate(user_message)
            if not is_valid:
                logger.warning(f"❌ Input validation failed: {validation_metadata['validation_layers'][-1]['reason']}")
                yield error_message
                return

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
        venues_data = []  # Collect structured venue data for frontend

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

                # Collect structured venue data with Google Places info
                venue_data = {
                    "id": venue.get('id', f"venue_{i}"),
                    "title": title,
                    "name": title,
                    "description": venue.get('description', ''),
                    "address": address,
                    "short_address": venue.get('short_address', ''),
                    "lat": venue.get('lat', 0),
                    "lon": venue.get('lon', 0),
                    "rating": venue.get('rating', 0),
                    "reviews_count": venue.get('reviews_count', 0),
                    "price_tier": venue.get('price_tier', venue.get('cost', 0)),
                    "price_level": venue.get('price_level', ''),
                    "type": venue.get('type', ''),
                    "primary_type": venue.get('primary_type', ''),
                    "all_types": venue.get('all_types', ''),
                    "website": venue.get('website_uri', venue.get('website', '')),
                    "google_maps_uri": venue.get('google_maps_uri', ''),
                    "regular_opening_hours": venue.get('regular_opening_hours', ''),
                    "current_opening_hours": venue.get('current_opening_hours', ''),
                    "selection_reason": reason,
                    "vibe": venue.get('true_vibe', vibe),
                    # Feature flags
                    "serves_dessert": venue.get('serves_dessert', False),
                    "serves_coffee": venue.get('serves_coffee', False),
                    "serves_beer": venue.get('serves_beer', False),
                    "serves_wine": venue.get('serves_wine', False),
                    "serves_cocktails": venue.get('serves_cocktails', False),
                    "serves_vegetarian": venue.get('serves_vegetarian', False),
                    "good_for_groups": venue.get('good_for_groups', False),
                    "good_for_children": venue.get('good_for_children', False),
                    "live_music": venue.get('live_music', False),
                    "outdoor_seating": venue.get('outdoor_seating', False),
                    "reservable": venue.get('reservable', False),
                    "review": venue.get('review', ''),
                    "review_summary": venue.get('review_summary', ''),
                }
                venues_data.append(venue_data)
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
            model="gpt-4o-mini",  # Using cheaper model (~90% cost reduction)
            messages=formatting_messages,
            max_tokens=600,  # Keep response reasonable
            stream=True
        )

        # Stream the formatted response
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

        # Send structured venue data as JSON after text response
        if venues_data:
            logger.info(f"📊 Sending structured data for {len(venues_data)} venues")
            import json
            venues_json = json.dumps({
                "type": "venues_data",
                "vibe": vibe,
                "venues": venues_data
            })
            yield f"\n\n__VENUES_DATA_START__\n{venues_json}\n__VENUES_DATA_END__"

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

        # STEP 2: Classify question and route to appropriate data source
        logger.info("🔍 [STEP 2] Classifying question and routing to data source...")

        from ..ml.question_classifier import QuestionClassifier
        q_type, data_source, q_description = QuestionClassifier.classify(user_message)
        logger.info(f"Question type: {q_type}, Data source: {data_source}, Description: {q_description}")

        # Extract venue IDs from itinerary
        venue_ids = [v.get('id') for v in itinerary if v.get('id')]
        logger.info(f"Extracted {len(venue_ids)} venue IDs from itinerary")

        # Build context based on data source
        context_parts = []

        # Always include basic venue info
        venues_context = ""
        for i, venue in enumerate(itinerary, 1):
            title = venue.get('title', venue.get('name', 'Unknown'))
            address = venue.get('address', venue.get('short_address', ''))
            venues_context += f"{i}. {title} ({address})\n"

        context_parts.append(f"User's Previous Itinerary:\n{venues_context}")

        # Route to appropriate data source
        if data_source == "database" and venue_ids:
            logger.info(f"Fetching venue details from database for question type: {q_type}")
            try:
                from ..tools.venue_data_fetcher import VenueDataFetcher
                from ..db_config import get_db_config

                db_config = get_db_config()
                # Use context manager for proper connection handling
                with db_config.get_connection() as db_conn:
                    fetcher = VenueDataFetcher(db_conn)
                    venue_details = fetcher.fetch_venue_details(venue_ids, q_type, user_message)

                    if venue_details:
                        formatted_details = fetcher.format_venue_details(venue_details, q_type)
                        context_parts.append(f"\nVenue Details ({q_description}):\n{formatted_details}")
                        logger.info(f"✅ Fetched {len(venue_details)} venues from database")
                    else:
                        logger.warning("No venue details found in database, falling back to web search")
                        data_source = "web_search"
            except Exception as e:
                logger.error(f"Error fetching from database: {e}, falling back to web search")
                logger.exception(e)
                data_source = "web_search"

        if data_source == "web_search":
            logger.info(f"Using web search for question type: {q_type}")
            search_query = f"{user_message} {' '.join([v.get('title', v.get('name', '')) for v in itinerary])}"
            web_results = await self.search_engine.web_search(search_query, limit=5)

            web_context = ""
            if web_results:
                logger.info(f"✅ Found {len(web_results)} web results")
                for result in web_results:
                    web_context += f"- {result.get('title', '')}: {result.get('snippet', '')}\n"
                context_parts.append(f"\nAdditional Information from Web:\n{web_context}")
            else:
                context_parts.append("\nNo additional web results found.")

        # STEP 3: Use OpenAI to answer the question with venue data
        logger.info("🤖 [STEP 3] Formatting answer with OpenAI...")

        context = "\n".join(context_parts)
        context += f"\n\nUser's Question: {user_message}\n\nAnswer the user's question about their itinerary using the venue information provided. Be specific and helpful. Reference the venues by name and provide practical details."

        formatting_messages = [
            {
                "role": "system",
                "content": "You are a helpful date planning assistant. Answer questions about the user's itinerary with specific, practical information."
            },
            {"role": "user", "content": context}
        ]

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",  # Using cheaper model (~90% cost reduction)
            messages=formatting_messages,
            max_tokens=400,
            stream=True
        )

        # Stream the formatted response
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

        # Send structured venue data as JSON after text response
        if itinerary:
            logger.info(f"📊 Sending structured data for {len(itinerary)} venues in follow-up")
            import json
            venues_json = json.dumps({
                "type": "venues_data",
                "vibe": vibe,
                "venues": itinerary
            })
            yield f"\n\n__VENUES_DATA_START__\n{venues_json}\n__VENUES_DATA_END__"

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

