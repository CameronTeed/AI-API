# heuristic_planner.py
# this is the greedy search approach - at each step pick the best looking venue
# faster than GA but might miss the globally optimal solution
# NOW USES POSTGRESQL DATABASE INSTEAD OF CSV

import pandas as pd
import numpy as np
import random
import math
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nlp_classifier
import db_manager
from planner_utils import (
    haversine_distance, is_open_now, add_similarity_scores, RELATED_TERMS,
    get_time_score_adjustment, suggest_itinerary_order, sort_by_date_sequence,
    get_venue_slot, venue_matches_type, get_venue_features
)
from config.scoring_config import ScoringConfig

# keeping this alias so old code still works
calculate_distance = haversine_distance


def check_type_match(venue, needed_types):
    # checks if venue matches any of the types the user asked for
    # uses venue_matches_type which checks type fields AND serves_* columns
    # returns the matched type or None if no match

    if not needed_types:
        return None

    from planner_utils import venue_matches_type

    # Check each needed type
    for t in needed_types:
        if venue_matches_type(venue, t):
            return t

    return None


def score_venue(venue, current_location, current_cost, target_vibes, budget_limit,
                needed_types=None, hidden_gem=False, visited_types=None,
                current_hour=None, stop_number=0):
    # this is the main scoring function - figures out how good a venue is
    # higher score = better venue for the itinerary
    # returns -1 if the venue is invalid (like over budget)
    #
    # factors we consider:
    # - does it match the vibe they want?
    # - is it highly rated?
    # - is it close to the previous stop?
    # - does it match a specific type they asked for (coffee, italian, etc)?
    # - is it a hidden gem if they want that?
    # - have we already picked a similar venue?
    # - does it make sense for this time of day?

    score = 0
    visited_types = visited_types or set()

    # hard constraint - if it puts us over budget, reject it immediately
    if current_cost + venue['cost'] > budget_limit:
        return -1

    # vibe matching - give points if the venue matches what they want
    venue_vibes = [v.strip().lower() for v in str(venue['true_vibe']).split(',')]

    if isinstance(target_vibes, list):
        match_count = sum(1 for v in target_vibes if v.lower() in venue_vibes)
        score += match_count * ScoringConfig.VIBE_MATCH_BONUS
    elif target_vibes and target_vibes.lower() in venue_vibes:
        score += ScoringConfig.VIBE_MATCH_BONUS

    # neutral vibes are ok for anything so small bonus
    if 'neutral' in venue_vibes:
        score += ScoringConfig.NEUTRAL_VIBE_BONUS

    # rating stuff - use bayesian average to handle venues with few reviews
    # basically a 5 star with 2 reviews shouldnt beat a 4.5 star with 500 reviews
    reviews = venue.get('reviews_count', 0)
    if pd.isna(reviews): reviews = 0
    rating = venue.get('rating', 3.0)

    if hidden_gem:
        # for hidden gems we want places with few reviews but good ratings
        if ScoringConfig.HIDDEN_GEM_MIN_REVIEWS <= reviews <= ScoringConfig.HIDDEN_GEM_MAX_REVIEWS:
            score += ScoringConfig.HIDDEN_GEM_BONUS
        elif reviews > 1000:
            score -= ScoringConfig.HIDDEN_GEM_POPULARITY_PENALTY  # too popular, not a hidden gem
        score += rating * ScoringConfig.HIDDEN_GEM_RATING_MULTIPLIER
    else:
        # bayesian average formula: (R * v + C * m) / (v + m)
        # R = actual rating, v = number of reviews
        # C = average rating across all venues (learned from data)
        # m = minimum reviews needed to trust the rating (learned from data)
        C = ScoringConfig.BAYESIAN_AVERAGE_CONSTANT
        m = ScoringConfig.BAYESIAN_MIN_REVIEWS
        bayesian_rating = (rating * reviews + C * m) / (reviews + m)
        score += bayesian_rating * ScoringConfig.RATING_MULTIPLIER

    # add a tiny bit of randomness so we dont always pick the same venues
    score += random.uniform(0, ScoringConfig.RANDOMNESS_MULTIPLIER) * (rating / 5.0)

    # distance penalty - we want venues close together so you dont have to travel far
    # using exponential penalty so really far venues get penalized more
    if current_location is not None:
        dist = calculate_distance(current_location['lat'], current_location['lon'],
                                  venue['lat'], venue['lon'])
        score -= (dist ** ScoringConfig.DISTANCE_EXPONENT) * ScoringConfig.DISTANCE_PENALTY_MULTIPLIER

    # type matching is super important - if they asked for coffee, prioritize cafes
    matched_type = check_type_match(venue, needed_types)
    if matched_type:
        score += ScoringConfig.TYPE_MATCH_BONUS  # big bonus, this is what they asked for!
    elif needed_types:
        # Use slot-based logic to determine penalty
        slot = get_venue_slot(venue)

        if slot == 'meal':
            # It's a restaurant but wrong type - MASSIVE penalty
            # This is the PHO for Italian dinner case
            score -= ScoringConfig.WRONG_CUISINE_PENALTY  # very harsh - we don't want wrong cuisines
        elif slot in ['activity', 'drinks', 'dessert', 'coffee']:
            # Complementary venue - small bonus for diversity
            score += ScoringConfig.COMPLEMENTARY_VENUE_BONUS
        else:
            # Unknown slot - mild penalty
            score -= ScoringConfig.UNKNOWN_SLOT_PENALTY

    # also use the precomputed similarity score
    if 'similarity_score' in venue:
        score += venue['similarity_score'] * 100

    # diversity - dont want to suggest 3 cafes in a row
    venue_type = str(venue.get('type', '')).lower()
    if venue_type and venue_type in visited_types:
        score -= ScoringConfig.REPEATED_TYPE_PENALTY  # penalty for repeating same type

    # bonus for trying something different
    venue_category = venue_type.split('_')[0] if '_' in venue_type else venue_type
    if venue_category and venue_category not in visited_types:
        score += ScoringConfig.NEW_CATEGORY_BONUS

    # time of day stuff - coffee in morning makes sense, not so much at midnight
    if current_hour is not None:
        estimated_hour = (current_hour + stop_number * 2) % 24
        time_multiplier = get_time_score_adjustment(venue_type, estimated_hour)
        if time_multiplier != 1.0:
            score *= time_multiplier

    # use csv columns for extra scoring
    if target_vibes:
        vibes_lower = [v.lower() for v in target_vibes] if isinstance(target_vibes, list) else [target_vibes.lower()]
        features = get_venue_features(venue)

        # Romantic dates: bonus for reservable, penalty for kids venues
        if 'romantic' in vibes_lower:
            if features['reservable']:
                score += ScoringConfig.ROMANTIC_RESERVABLE_BONUS
            if features['good_for_children']:
                score -= ScoringConfig.ROMANTIC_KIDS_PENALTY

        # Outdoor vibes: bonus for outdoor seating
        if 'outdoors' in vibes_lower or 'outdoor' in vibes_lower:
            if features['outdoor_seating']:
                score += ScoringConfig.OUTDOOR_SEATING_BONUS

        # Family vibes: bonus for kid-friendly
        if 'family' in vibes_lower:
            if features['good_for_children']:
                score += ScoringConfig.FAMILY_KIDS_BONUS

        # Energetic vibes: bonus for live music
        if 'energetic' in vibes_lower:
            if features['live_music']:
                score += ScoringConfig.ENERGETIC_LIVE_MUSIC_BONUS

        # Group date: bonus for group-friendly venues
        if any(v in vibes_lower for v in ['group', 'groups', 'friends', 'party']):
            if features['good_for_groups']:
                score += ScoringConfig.GROUP_FRIENDLY_BONUS

    return score

def run_heuristic_search(df, target_vibes, budget_limit, itinerary_length=3, location_filter=None, target_types=None, hidden_gem=False, current_dt=None, semantic_query=None, randomness=0.2):
    # main function - builds an itinerary using greedy search
    # basically at each step we just pick the best looking venue and add it
    # not guaranteed to find the absolute best combo but its fast and works pretty well
    # randomness parameter controls how often we pick randomly vs best (0=always best, 1=very random)

    # learn from data if we havent already (data-driven approach)
    from planner_utils import initialize_from_data
    initialize_from_data(df)

    plan = []
    current_cost = 0
    current_location = None
    visited_ids = set()  # dont want to pick the same place twice
    visited_types = set()  # track types for diversity
    needed_types = set(target_types) if target_types else set()

    # get current hour so we can score venues by time appropriateness
    from datetime import datetime
    if current_dt is None:
        current_dt = datetime.now()
    current_hour = current_dt.hour

    # precompute a searchable text column - way faster than checking each field separately
    df['_search_text'] = (
        df['type'].fillna('').str.replace('_', ' ') + ' ' +
        df['all_types'].fillna('').str.replace('_', ' ') + ' ' +
        df['primary_type_display_name'].fillna('') + ' ' +
        df['name'].fillna('')
    ).str.lower()

    df['similarity_score'] = 0.0

    # type matching using vectorized string ops (much faster than loops)
    # Uses RELATED_TERMS which is learned from the data, not hardcoded
    if target_types:
        for t in target_types:
            t_lower = t.lower()
            # direct match gets more points
            mask = df['_search_text'].str.contains(t_lower, regex=False)
            df.loc[mask, 'similarity_score'] += 2.0

            # related terms get slightly fewer points (learned from data)
            if t_lower in RELATED_TERMS:
                for rel in RELATED_TERMS[t_lower]:
                    rel_mask = df['_search_text'].str.contains(rel, regex=False)
                    df.loc[rel_mask, 'similarity_score'] += 1.5

    # also boost venues that match the requested vibes
    if target_vibes:
        vibe_col = df['true_vibe'].fillna('').str.lower()
        for v in target_vibes:
            mask = vibe_col.str.contains(v.lower(), regex=False)
            df.loc[mask, 'similarity_score'] += 0.5

    # location filter - if they said a specific area only look there
    if location_filter and location_filter.lower() != "ottawa":
        loc_mask = df['address'].str.contains(location_filter, case=False, na=False) | \
                   df['short_address'].str.contains(location_filter, case=False, na=False)

        if loc_mask.any():
            df = df[loc_mask].copy()
        # if no venues match location, just use all of ottawa

    # ok now the actual greedy search - for each stop find the best venue
    for step in range(itinerary_length):
        # collect all valid venues with their scores
        scored_venues = []

        for _, venue in df.iterrows():
            if venue['id'] in visited_ids:
                continue

            score = score_venue(venue, current_location, current_cost, target_vibes,
                              budget_limit, needed_types, hidden_gem, visited_types,
                              current_hour=current_hour, stop_number=step)

            if score > -1:  # valid venue
                scored_venues.append((score, venue))

        if not scored_venues:
            continue

        # sort by score descending
        scored_venues.sort(key=lambda x: x[0], reverse=True)

        # randomness controls selection:
        # 0 = always pick best, 1 = pick randomly from top candidates
        if randomness > 0 and len(scored_venues) > 1 and random.random() < randomness:
            # pick from top N candidates based on randomness level
            # higher randomness = consider more candidates
            top_n = max(2, int(len(scored_venues) * randomness * 0.5))
            top_n = min(top_n, len(scored_venues))
            best_score, best_venue = random.choice(scored_venues[:top_n])
        else:
            # deterministic - just pick the best one
            best_score, best_venue = scored_venues[0]

        # if we found something good, add it to the plan
        if best_venue is not None and best_score > -1:
            # build a reason string so we can explain why we picked this venue
            reasons = []
            v_vibes = str(best_venue.get('true_vibe', '')).split(', ')

            if target_vibes and any(v in v_vibes for v in target_vibes):
                reasons.append(f"matches '{target_vibes[0] if isinstance(target_vibes, list) else target_vibes}' vibe")

            if best_venue.get('similarity_score', 0) > 0.6:
                reasons.append("matches your request perfectly")
            elif best_venue.get('similarity_score', 0) > 0.4:
                reasons.append("good match")

            if best_venue['rating'] >= 4.5:
                reasons.append("highly rated")
            elif hidden_gem and 10 <= best_venue.get('reviews_count', 0) <= 300:
                reasons.append("is a hidden gem")

            matched_type = check_type_match(best_venue, needed_types)
            if matched_type:
                reasons.append(f"is a {matched_type}")

            if not reasons:
                reasons.append("fits the itinerary")

            best_venue['selection_reason'] = ", ".join(reasons).capitalize()

            plan.append(best_venue)
            visited_ids.add(best_venue['id'])
            current_cost += best_venue['cost']
            current_location = best_venue

            # remember this type so we dont pick too many of the same thing
            venue_type = str(best_venue.get('type', '')).lower()
            visited_types.add(venue_type)

            # if this venue fulfilled a type request, remove it from needed
            fulfilled_type = check_type_match(best_venue, needed_types)
            if fulfilled_type:
                needed_types.remove(fulfilled_type)

        else:
            break  # no valid venues left

    # sort into logical date sequence (activity -> meal -> drinks -> dessert)
    plan = sort_by_date_sequence(plan)
    return plan


# Integration function for AI Orchestrator
def plan_date(preferences):
    """
    Integration wrapper for AI Orchestrator
    Plans a date from preferences dictionary

    Args:
        preferences: dict with keys:
            - venues_df: DataFrame of venues
            - start_location: tuple (lat, lon)
            - vibe: str, target vibe
            - budget_range: tuple (min, max) or None
            - max_venues: int, max number of venues
            - max_duration_hours: int, max duration

    Returns:
        dict with success status, itinerary, vibe, num_venues
    """
    try:
        # Get venues from database or use provided dataframe
        venues_df = preferences.get('venues_df')

        if venues_df is None or venues_df.empty:
            # Try to load from database
            db_manager.init_db_pool()
            venues_df = db_manager.get_all_venues()

            if venues_df is None or venues_df.empty:
                return {'success': False, 'error': 'No venues available in database'}

        start_location = preferences.get('start_location', (45.4215, -75.6972))
        vibe = preferences.get('vibe', 'casual')
        budget_range = preferences.get('budget_range')
        max_venues = preferences.get('max_venues', 5)

        # Set budget limit
        budget_limit = budget_range[1] if budget_range else 150

        # Plan the date
        itinerary = plan_date_heuristic(
            venues_df,
            start_location,
            target_vibes=[vibe],
            budget_limit=budget_limit,
            itinerary_length=max_venues
        )

        return {
            'success': True,
            'itinerary': itinerary,
            'vibe': vibe,
            'num_venues': len(itinerary)
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
