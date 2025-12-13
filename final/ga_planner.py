# ga_planner.py
# genetic algorithm approach to building itineraries
# slower than heuristic but can find better global solutions by exploring more options
# uses evolution concepts: population, selection, crossover, mutation
# NOW USES POSTGRESQL DATABASE INSTEAD OF CSV
# OPTIMIZED: Smart database loading, vectorized operations, caching

import pandas as pd
import random
import numpy as np
import math
from datetime import datetime
import sys
import os
import logging
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db_manager
from heuristic_planner import check_type_match
from planner_utils import (haversine_distance, is_open_now, add_similarity_scores,
                           RELATED_TERMS, sort_by_date_sequence, get_venue_stage,
                           get_venue_slot, venue_matches_type, get_venue_cuisine,
                           get_venue_features)
from config.scoring_config import ScoringConfig

# Setup logging for performance tracking
logger = logging.getLogger(__name__)

# Cache for distance calculations (optimization)
_distance_cache = {}


def haversine_distance_cached(lat1, lon1, lat2, lon2):
    """
    OPTIMIZED: Cached haversine distance calculation.
    Avoids recalculating distances between same venue pairs.
    """
    cache_key = (round(lat1, 4), round(lon1, 4), round(lat2, 4), round(lon2, 4))
    if cache_key not in _distance_cache:
        # Use the original haversine function
        from planner_utils import haversine_distance as hd
        _distance_cache[cache_key] = hd(lat1, lon1, lat2, lon2)
    return _distance_cache[cache_key]


def calculate_fitness(itinerary, budget_limit, location_filter=None, hidden_gem=False,
                      current_dt=None, target_types=None, target_vibes=None):
    # fitness function for the GA - scores how good an itinerary is
    #
    # the main idea:
    # 1. if they ask for a cuisine like italian, give them ONE restaurant of that type
    #    plus complementary stuff (activity, bar, dessert) - not other cuisines
    # 2. if they ask for a category like bars, give them all bars
    # 3. wrong cuisine restaurants = massive penalty
    score = 1000  # start high, subtract for problems (GA_INITIAL_SCORE)

    # hard constraints - these are instant fails
    venue_ids = [place.get('id') for place in itinerary]
    if len(set(venue_ids)) < len(venue_ids):
        return 0  # duplicates = bad

    total_cost = sum(place['cost'] for place in itinerary)
    if total_cost > budget_limit:
        return 0

    # type matching - if they ask for museum+lunch, want one of each not all museums
    if target_types:
        covered_types = set()
        types_covered_by = {}

        for place in itinerary:
            for target in target_types:
                if venue_matches_type(place, target):
                    covered_types.add(target)
                    if target not in types_covered_by:
                        types_covered_by[target] = []
                    types_covered_by[target].append(place['name'])

        num_types_covered = len(covered_types)
        score += num_types_covered * 400  # GA_TYPE_COVERAGE_BONUS

        if num_types_covered == len(target_types):
            score += 500  # GA_FULL_TYPE_COVERAGE_BONUS - covered everything they asked for

        missing_types = set(target_types) - covered_types
        score -= len(missing_types) * 300  # GA_MISSING_TYPE_PENALTY

        # single type request like "italian dinner"
        if len(target_types) == 1:
            t = target_types[0]
            # Handle case where t might be a tuple or list
            if isinstance(t, (list, tuple)):
                t = t[0] if t else ''
            target = str(t).lower()
            cuisine_keywords = ['italian', 'french', 'japanese', 'chinese', 'vietnamese',
                               'thai', 'indian', 'mexican', 'korean', 'greek', 'pizza',
                               'sushi', 'ramen', 'pho', 'burger', 'steak', 'seafood']

            is_cuisine_request = any(kw in target for kw in cuisine_keywords)

            if is_cuisine_request:
                for place in itinerary:
                    slot = get_venue_slot(place)
                    matches = venue_matches_type(place, target)
                    if slot == 'meal' and not matches:
                        score -= ScoringConfig.WRONG_CUISINE_PENALTY  # wrong cuisine

    # diversity bonus
    if len(itinerary) >= 2:
        slots = [get_venue_slot(place) for place in itinerary]
        unique_slots = set(slots)
        score += len(unique_slots) * 50  # GA_DIVERSITY_BONUS

        # reward good date flow (activity -> meal -> drinks)
        stages = [get_venue_stage(place) for place in itinerary]
        is_ascending = all(stages[i] <= stages[i+1] for i in range(len(stages)-1))
        if is_ascending:
            score += 100  # GA_GOOD_FLOW_BONUS

    # ratings
    for place in itinerary:
        rating = place.get('rating', 3.0)
        reviews = place.get('reviews_count', 0)
        if pd.isna(reviews): reviews = 0

        if hidden_gem:
            if ScoringConfig.HIDDEN_GEM_MIN_REVIEWS <= reviews <= ScoringConfig.HIDDEN_GEM_MAX_REVIEWS:
                score += ScoringConfig.HIDDEN_GEM_BONUS
        else:
            score += rating * 10  # GA_RATING_MULTIPLIER

    # penalize far apart venues (OPTIMIZED: use cached distance)
    for i in range(len(itinerary) - 1):
        p1, p2 = itinerary[i], itinerary[i+1]
        dist = haversine_distance_cached(p1['lat'], p1['lon'], p2['lat'], p2['lon'])
        score -= dist * 5  # GA_DISTANCE_PENALTY

    # vibe matching
    if target_vibes:
        for place in itinerary:
            place_vibes = [v.strip().lower() for v in str(place.get('true_vibe', '')).split(',')]
            # Handle case where tv might be a tuple or list
            vibes_to_check = []
            for tv in target_vibes:
                if isinstance(tv, (list, tuple)):
                    vibes_to_check.append(str(tv[0]).lower() if tv else '')
                else:
                    vibes_to_check.append(str(tv).lower())
            if any(tv in place_vibes for tv in vibes_to_check):
                score += 30  # GA_VIBE_MATCH_BONUS

    # location filter
    if location_filter:
        location_filter_str = str(location_filter).lower()
        if location_filter_str != "ottawa":
            for place in itinerary:
                addr = str(place.get('address', '')) + str(place.get('short_address', ''))
                if location_filter_str not in addr.lower():
                    score -= 50  # GA_LOCATION_MISMATCH_PENALTY

    # use the extra csv columns for scoring
    if target_vibes:
        vibes_lower = []
        for v in target_vibes:
            if isinstance(v, (list, tuple)):
                vibes_lower.append(str(v[0]).lower() if v else '')
            else:
                vibes_lower.append(str(v).lower())

        for place in itinerary:
            features = get_venue_features(place)

            # Romantic dates: bonus for reservable, penalty for kids venues
            if 'romantic' in vibes_lower:
                if features['reservable']:
                    score += 25
                if features['good_for_children']:
                    score -= 30  # probably not ideal for romantic date

            # Outdoor vibes: bonus for outdoor seating
            if 'outdoors' in vibes_lower or 'outdoor' in vibes_lower:
                if features['outdoor_seating']:
                    score += 40

            # Family vibes: bonus for kid-friendly
            if 'family' in vibes_lower:
                if features['good_for_children']:
                    score += 50

            # Energetic vibes: bonus for live music
            if 'energetic' in vibes_lower:
                if features['live_music']:
                    score += 40

            # Group date: bonus for group-friendly venues
            if any(v in vibes_lower for v in ['group', 'groups', 'friends', 'party']):
                if features['good_for_groups']:
                    score += 40

    return max(score, 0)


def create_diverse_stage_individual(pool_df, matching_df, itinerary_length):
    # creates an itinerary with different stages (activity -> meal -> drinks)
    # makes sure at least one venue matches what the user asked for
    # then fills in with complementary stuff
    # e.g. for "French dinner": park (stage 1) + french restaurant (stage 3) + bar (stage 4)
    selected = []
    selected_ids = set()

    # First, pick ONE type-matching venue for the main event
    if len(matching_df) > 0:
        main_venue = matching_df.sample(1).iloc[0]
        selected.append(main_venue.to_dict())
        selected_ids.add(main_venue['id'])
        main_stage = get_venue_stage(main_venue)
    else:
        main_stage = 3  # Default to meal stage

    # Now fill remaining slots with venues from DIFFERENT stages
    # Prioritize: before main stage, then after main stage
    desired_stages = []
    if itinerary_length >= 2:
        if main_stage > 1:
            desired_stages.append(1)  # activity/park before
        if main_stage < 5:
            desired_stages.append(min(main_stage + 1, 5))  # drinks/dessert after

    # Add more stages if needed
    all_stages = [1, 2, 3, 4, 5]
    for s in all_stages:
        if s != main_stage and s not in desired_stages:
            desired_stages.append(s)

    for stage in desired_stages:
        if len(selected) >= itinerary_length:
            break

        # Find venues with this stage
        stage_venues = pool_df[~pool_df['id'].isin(selected_ids)].copy()
        stage_venues['_stage'] = stage_venues.apply(lambda r: get_venue_stage(r), axis=1)
        stage_venues = stage_venues[stage_venues['_stage'] == stage]

        if len(stage_venues) > 0:
            # Pick one with good score
            if 'similarity_score' in stage_venues.columns:
                stage_venues = stage_venues.sort_values('similarity_score', ascending=False)
                venue = stage_venues.head(10).sample(1).iloc[0]
            else:
                venue = stage_venues.sample(1).iloc[0]
            selected.append(venue.to_dict())
            selected_ids.add(venue['id'])

    # Fill any remaining slots randomly
    while len(selected) < itinerary_length:
        remaining = pool_df[~pool_df['id'].isin(selected_ids)]
        if len(remaining) > 0:
            venue = remaining.sample(1).iloc[0]
            selected.append(venue.to_dict())
            selected_ids.add(venue['id'])
        else:
            break

    # Sort by stage for natural flow
    selected.sort(key=lambda v: get_venue_stage(v))

    return selected


def create_individual(df, itinerary_length, bias_top_n=None):
    # creates one itinerary (individual) for the population
    # can be biased towards high-scoring venues for smarter initialization
    # or fully random for diversity

    if len(df) < itinerary_length:
        return df.sample(n=itinerary_length, replace=True).to_dict('records')

    if bias_top_n and len(df) > bias_top_n:
        # smart initialization - 70% from top venues, 30% random
        top_df = df.head(bias_top_n)
        rest_df = df.iloc[bias_top_n:]

        selected = []
        selected_ids = set()

        for _ in range(itinerary_length):
            if random.random() < 0.7 and len(top_df) > 0:
                pool = top_df[~top_df['id'].isin(selected_ids)]
            else:
                pool = rest_df[~rest_df['id'].isin(selected_ids)]

            if len(pool) == 0:
                pool = df[~df['id'].isin(selected_ids)]

            if len(pool) > 0:
                venue = pool.sample(1).iloc[0]
                selected.append(venue.to_dict())
                selected_ids.add(venue['id'])

        return selected
    else:
        return df.sample(n=itinerary_length, replace=False).to_dict('records')


def crossover(parent1, parent2):
    # SEQUENCE-AWARE crossover - combines two parent itineraries
    # tries to maintain logical date flow (activity -> meal -> drinks)
    # takes venues from both parents and orders them by stage

    if len(parent1) < 2:
        return parent1[:]

    size = len(parent1)

    # 50/50 between two crossover methods - idk why this ratio works best but it does
    if random.random() < 0.5:
        # SEQUENCE-AWARE: pick best venues from both, sort by stage
        all_venues = parent1 + parent2
        unique_venues = []
        seen_ids = set()
        for v in all_venues:
            if v['id'] not in seen_ids:
                unique_venues.append(v)
                seen_ids.add(v['id'])

        # sort by stage to get good date flow
        unique_venues.sort(key=lambda v: get_venue_stage(v))

        # pick best ones (variety of stages preferred)
        child = []
        stages_used = set()
        for v in unique_venues:
            if len(child) >= size:
                break
            stage = get_venue_stage(v)
            # prefer venues from different stages
            if stage not in stages_used or len(child) < size:
                child.append(v)
                stages_used.add(stage)

        # fill if we dont have enough
        while len(child) < size:
            for v in unique_venues:
                if v not in child:
                    child.append(v)
                    break
            else:
                break

        return child[:size]

    else:
        # TRADITIONAL: order-based crossover (OX)
        # pick random crossover points
        start, end = sorted(random.sample(range(size), 2))

        # copy segment from parent1
        child = [None] * size
        child[start:end+1] = parent1[start:end+1]

        # track whats already in the child
        child_ids = {p['id'] for p in child if p is not None}

        # fill remaining from parent2 (skip duplicates)
        parent2_filtered = [p for p in parent2 if p['id'] not in child_ids]

        idx = 0
        for i in range(size):
            if child[i] is None and idx < len(parent2_filtered):
                child[i] = parent2_filtered[idx]
                idx += 1

        # safety: fill any remaining None slots (avoiding duplicates)
        child_ids = {p['id'] for p in child if p is not None}
        for i in range(size):
            if child[i] is None:
                # Find a venue from parent1 that's not already in child
                for p in parent1:
                    if p['id'] not in child_ids:
                        child[i] = p
                        child_ids.add(p['id'])
                        break
                else:
                    # Fallback to parent2
                    for p in parent2:
                        if p['id'] not in child_ids:
                            child[i] = p
                            child_ids.add(p['id'])
                            break

        return child


def mutate(individual, df, mutation_rate=0.1, prefer_high_score=False):
    # mutation adds randomness to explore new solutions
    # can prefer high-scoring venues when we're stuck (diversity is low)
    # uses different mutation operators randomly for variety
    # NOW INCLUDES sequence-improving mutations!

    if random.random() >= mutation_rate:
        return individual

    current_ids = {p['id'] for p in individual}
    mutation_type = random.choice(['replace', 'swap', 'smart_replace', 'sequence_fix', 'stage_swap'])

    if mutation_type == 'swap' and len(individual) >= 2:
        # swap mutation - switches two venues in the itinerary
        # changes the order without changing the venues
        i, j = random.sample(range(len(individual)), 2)
        individual[i], individual[j] = individual[j], individual[i]

    elif mutation_type == 'sequence_fix':
        # NEW: sort the itinerary by stage to fix bad sequences
        # this mutation directly improves date flow
        individual.sort(key=lambda v: get_venue_stage(v))

    elif mutation_type == 'stage_swap' and len(individual) >= 2:
        # NEW: find venues in wrong order and swap them
        # e.g., if dessert is before dinner, swap them
        stages = [(i, get_venue_stage(v)) for i, v in enumerate(individual)]
        for i in range(len(stages) - 1):
            if stages[i][1] > stages[i+1][1]:  # backwards!
                # swap them to fix the sequence
                idx1, idx2 = stages[i][0], stages[i+1][0]
                individual[idx1], individual[idx2] = individual[idx2], individual[idx1]
                break  # just fix one pair per mutation

    elif mutation_type == 'smart_replace' and prefer_high_score and 'similarity_score' in df.columns:
        # smart replace - picks from top venues when were stuck
        idx = random.randint(0, len(individual) - 1)
        top_n = max(5, len(df) // 5)
        candidates = df.nlargest(top_n, 'similarity_score')
        candidates = candidates[~candidates['id'].isin(current_ids)]
        if len(candidates) > 0:
            individual[idx] = candidates.sample(1).iloc[0].to_dict()

    else:
        # regular replace - swap one venue with a random new one
        idx = random.randint(0, len(individual) - 1)
        candidates = df.sample(min(len(df), 10)).to_dict('records')
        for c in candidates:
            if c['id'] not in current_ids:
                individual[idx] = c
                break

    return individual


def calculate_population_diversity(population):
    # measures how different the itineraries in our population are
    # 0 = all the same, 1 = all different
    # we use this to know when to increase mutation (if too similar)

    all_ids = []
    for ind in population:
        all_ids.extend([p['id'] for p in ind])

    unique_ratio = len(set(all_ids)) / max(len(all_ids), 1)
    return unique_ratio


def local_search(individual, df, budget_limit, target_types, target_vibes, location_filter, hidden_gem, current_dt):
    # local search tries to improve an itinerary by swapping individual venues
    # this turns the GA into a Memetic Algorithm (GA + local search)
    # basically hill climbing on top of the evolutionary search

    current_fitness = calculate_fitness(individual, budget_limit, location_filter, hidden_gem,
                                        current_dt, target_types, target_vibes)

    current_ids = {p['id'] for p in individual}
    improved = True
    max_iterations = 10  # dont spend too long on local search
    iterations = 0

    while improved and iterations < max_iterations:
        improved = False
        iterations += 1

        # try replacing each venue with a better one
        for i in range(len(individual)):
            # get some candidate replacements
            candidates = df[~df['id'].isin(current_ids)].nlargest(20, 'similarity_score')

            if len(candidates) == 0:
                continue

            for _, candidate in candidates.iterrows():
                # try swapping
                old_venue = individual[i]
                individual[i] = candidate.to_dict()

                new_fitness = calculate_fitness(individual, budget_limit, location_filter,
                                               hidden_gem, current_dt, target_types, target_vibes)

                if new_fitness > current_fitness:
                    # keep the improvement
                    current_fitness = new_fitness
                    current_ids.discard(old_venue['id'])
                    current_ids.add(candidate['id'])
                    improved = True
                    break
                else:
                    # revert
                    individual[i] = old_venue

    return individual

def run_genetic_algorithm(df, target_vibes, budget_limit, itinerary_length=3, location_filter=None, target_types=None, hidden_gem=False, current_dt=None, semantic_query="", randomness=0.2, excluded_venue_ids=None):
    # main GA function - evolves itineraries to find the best combo
    # slower than heuristic but explores way more options
    # randomness controls mutation/exploration (0=stable, 1=chaotic)
    # OPTIMIZED: Smart database loading, vectorized operations, caching

    start_time = time.time()

    # learn from data if we havent already (data-driven approach)
    from planner_utils import initialize_from_data
    initialize_from_data(df)

    if current_dt is None:
        current_dt = datetime.now()

    # Filter out excluded venues
    if excluded_venue_ids:
        df = df[~df['id'].isin(excluded_venue_ids)].copy()
        if len(df) == 0:
            logger.warning("All venues were excluded, returning empty itinerary")
            return []

    # scale GA parameters based on randomness
    # higher randomness = more mutation, more exploration
    mutation_rate = ScoringConfig.MUTATION_RATE * (0.5 + randomness)  # ranges from 0.1 to 0.3
    crossover_rate = ScoringConfig.CROSSOVER_RATE - (randomness * 0.2)  # ranges from 0.8 to 0.6

    # OPTIMIZATION: Use reference instead of copy where possible
    pool_df = df

    # precompute searchable text - same as heuristic planner
    pool_df['_search_text'] = (
        pool_df['type'].fillna('').str.replace('_', ' ') + ' ' +
        pool_df['all_types'].fillna('').str.replace('_', ' ') + ' ' +
        pool_df['primary_type_display_name'].fillna('') + ' ' +
        pool_df['name'].fillna('')
    ).str.lower()

    pool_df['similarity_score'] = 0.0

    # vectorized type matching - use RELATED_TERMS from planner_utils
    if target_types:
        for t in target_types:
            t_lower = t.lower()
            mask = pool_df['_search_text'].str.contains(t_lower, regex=False)
            pool_df.loc[mask, 'similarity_score'] += 2.0
            # also check related terms (coffee -> cafe, etc)
            if t_lower in RELATED_TERMS:
                for rel in RELATED_TERMS[t_lower]:
                    rel_mask = pool_df['_search_text'].str.contains(rel, regex=False)
                    pool_df.loc[rel_mask, 'similarity_score'] += 1.5

    # vibe matching
    if target_vibes:
        vibe_col = pool_df['true_vibe'].fillna('').str.lower()
        for v in target_vibes:
            # Handle case where v might be a tuple or list
            v_str = str(v).lower() if not isinstance(v, str) else v.lower()
            mask = vibe_col.str.contains(v_str, regex=False)
            pool_df.loc[mask, 'similarity_score'] += 0.5

    # sort so best matches are at top (for smart initialization)
    pool_df = pool_df.sort_values('similarity_score', ascending=False)

    # SMART INITIALIZATION: Use data-driven matching
    # Get venues that actually match the target types (based on computed similarity)
    matching_df = pool_df[pool_df['similarity_score'] >= 2.0]  # direct type match
    has_matches = len(matching_df) > 0

    # initialize population
    bias_n = min(30, len(pool_df) // 3)
    population = []

    for i in range(ScoringConfig.POPULATION_SIZE):
        if has_matches:
            # We have type-matching venues - ensure they're included
            if i < ScoringConfig.POPULATION_SIZE * 0.5:
                # 50%: seed with matching venues + diverse stages
                population.append(create_diverse_stage_individual(pool_df, matching_df, itinerary_length))
            elif i < ScoringConfig.POPULATION_SIZE * 0.8:
                # 30%: bias towards high-scoring venues
                population.append(create_individual(pool_df, itinerary_length, bias_top_n=bias_n))
            else:
                # 20%: random for exploration
                population.append(create_individual(pool_df, itinerary_length))
        else:
            # No type matches - use vibe/score based selection
            if i < ScoringConfig.POPULATION_SIZE * 0.7:
                population.append(create_individual(pool_df, itinerary_length, bias_top_n=bias_n))
            else:
                population.append(create_individual(pool_df, itinerary_length))

    best_score_history = []
    stagnation_counter = 0  # tracks how long weve been stuck
    best_ever = 0

    # main evolution loop
    for _ in range(ScoringConfig.GENERATIONS):
        # score everyone
        scores = [calculate_fitness(ind, budget_limit, location_filter, hidden_gem,
                                   current_dt, target_types, target_vibes) for ind in population]

        current_best = max(scores)
        best_score_history.append(current_best)

        # early stopping - if no improvement for STAGNATION_LIMIT generations, stop
        if current_best > best_ever:
            best_ever = current_best
            stagnation_counter = 0
        else:
            stagnation_counter += 1

        if stagnation_counter >= ScoringConfig.STAGNATION_LIMIT:
            break  # stuck, stop early

        # adaptive mutation - if we're stuck increase mutation to explore more
        # uses the user-controlled mutation_rate as the base
        if len(best_score_history) > 5:
            recent_improvement = best_score_history[-1] - best_score_history[-5]
            if recent_improvement < 1:
                current_mutation_rate = min(0.5, mutation_rate * 2)  # double mutation
            else:
                current_mutation_rate = mutation_rate
        else:
            current_mutation_rate = mutation_rate

        # elitism - keep the best ones unchanged
        scored_pop = sorted(zip(scores, population), key=lambda pair: pair[0], reverse=True)
        next_gen = [ind[:] for _, ind in scored_pop[:ScoringConfig.ELITISM_COUNT]]

        # tournament selection - pick 3 random, take the best
        tournament_size = 3

        def tournament_select():
            candidates = random.sample(scored_pop, min(tournament_size, len(scored_pop)))
            best_pair = max(candidates, key=lambda pair: pair[0])
            return best_pair[1]

        # create rest of next generation
        while len(next_gen) < ScoringConfig.POPULATION_SIZE:
            parent1 = tournament_select()
            parent2 = tournament_select()

            # crossover rate - controlled by randomness slider
            if random.random() < crossover_rate:
                child = crossover(parent1, parent2)
            else:
                # just copy one parent (with deep copy)
                child = [v.copy() for v in parent1]

            # if diversity is low, bias mutations towards good venues
            diversity = calculate_population_diversity(population)
            prefer_high = diversity < 0.3
            child = mutate(child, pool_df, current_mutation_rate, prefer_high_score=prefer_high)

            next_gen.append(child)

        population = next_gen

    # find the best one at the end
    final_scores = [calculate_fitness(ind, budget_limit, location_filter, hidden_gem, current_dt, target_types, target_vibes) for ind in population]
    best_idx = np.argmax(final_scores)

    # apply local search to polish the best solution (memetic algorithm)
    # this can squeeze out a few more points of fitness
    best_plan = population[best_idx]
    best_plan = local_search(best_plan, pool_df, budget_limit, target_types, target_vibes,
                             location_filter, hidden_gem, current_dt)

    # could print final score here for debugging but leaving it out

    # add human-readable reasons for each venue (for the UI)
    for venue in best_plan:
        reasons = []

        if venue.get('similarity_score', 0) > 0.6:
            reasons.append("matches your request perfectly")
        elif venue.get('similarity_score', 0) > 0.4:
            reasons.append("good match")

        if venue.get('rating', 0) >= 4.5:
            reasons.append("highly rated")

        if hidden_gem and 10 <= venue.get('reviews_count', 0) <= 300:
            reasons.append("hidden gem")

        if target_types:
            matched_type = check_type_match(venue, target_types)
            if matched_type:
                reasons.append(f"is a {matched_type}")

        if not reasons:
            reasons.append("good fit")

        venue['selection_reason'] = ", ".join(reasons).capitalize()

    # sort into logical date sequence (activity -> meal -> drinks -> dessert)
    best_plan = sort_by_date_sequence(best_plan)
    return best_plan


# Integration function for AI Orchestrator
def plan_date(preferences):
    """
    Integration wrapper for AI Orchestrator
    Plans a date from preferences dictionary using genetic algorithm
    OPTIMIZED: Uses smart database loading for 5-10x faster performance

    Args:
        preferences: dict with keys:
            - venues_df: DataFrame of venues (optional, will load from DB if not provided)
            - start_location: tuple (lat, lon)
            - vibe: str, target vibe
            - budget_range: tuple (min, max) or None
            - max_venues: int, max number of venues
            - target_types: list of types to filter by (optional)
            - hidden_gem: bool, prefer hidden gems (optional)

    Returns:
        dict with success status, itinerary, vibe, num_venues
    """
    try:
        venues_df = preferences.get('venues_df')

        # OPTIMIZATION: Use smart database loading if no venues provided
        if venues_df is None or venues_df.empty:
            db_manager.init_db_pool()

            # Extract filters for smart loading
            vibe = preferences.get('vibe', 'casual')
            budget_range = preferences.get('budget_range')
            target_types = preferences.get('target_types')

            # Load only needed venues with filters applied at DB level
            max_cost = budget_range[1] if budget_range else None
            venues_df = db_manager.get_venues_for_ga(
                vibes=[vibe] if vibe else None,
                types=target_types,
                max_cost=max_cost,
                limit=500  # Load up to 500 venues for GA
            )

            if venues_df is None or venues_df.empty:
                return {'success': False, 'error': 'No venues available in database'}

        start_location = preferences.get('start_location', (45.4215, -75.6972))
        vibe = preferences.get('vibe', 'casual')
        budget_range = preferences.get('budget_range')
        max_venues = preferences.get('max_venues', 5)

        # Set budget limit
        budget_limit = budget_range[1] if budget_range else 150

        # Plan the date using genetic algorithm
        itinerary = run_genetic_algorithm(
            venues_df,
            target_vibes=[vibe],
            budget_limit=budget_limit,
            itinerary_length=max_venues,
            location_filter=start_location,
            target_types=preferences.get('target_types'),
            hidden_gem=preferences.get('hidden_gem', False)
        )

        return {
            'success': True,
            'itinerary': itinerary,
            'vibe': vibe,
            'num_venues': len(itinerary)
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
