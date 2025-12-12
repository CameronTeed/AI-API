# planner_utils.py
# shared helper functions for the planners - keeps things DRY
#
# SIMPLE APPROACH:
# 1. Venues belong to one of 4 SLOTS: activity, meal, drinks, dessert
# 2. Slot is determined by checking all_types for keywords
# 3. For diverse dates: want different slots (activity -> meal -> drinks)
# 4. For same-type requests (3 bars): want all same type

import math
import json
import pandas as pd
from datetime import datetime
from collections import defaultdict

_DATA_LEARNED = False

# slots - each venue belongs to one of these categories
def get_venue_slot(venue):
    all_types = str(venue.get('all_types', '')).lower()
    venue_type = str(venue.get('type', '')).lower()
    combined = all_types + ' ' + venue_type

    # dessert
    if any(kw in combined for kw in ['bakery', 'ice_cream', 'dessert', 'pastry', 'donut', 'candy']):
        return 'dessert'

    # drinks but not restaurant-bars
    if any(kw in combined for kw in ['bar', 'pub', 'brewery', 'nightclub', 'lounge']):
        if 'restaurant' not in venue_type:
            return 'drinks'

    if 'restaurant' in combined or 'food' in combined or 'dining' in combined:
        return 'meal'

    if any(kw in combined for kw in ['park', 'museum', 'gallery', 'cinema', 'theater', 'theatre',
                                      'bowling', 'spa', 'gym', 'recreation', 'attraction',
                                      'amusement', 'zoo', 'aquarium', 'skating']):
        return 'activity'

    if any(kw in combined for kw in ['coffee', 'cafe', 'café', 'tea_house']):
        return 'coffee'

    return 'other'


def get_venue_cuisine(venue):
    # returns the cuisine type for a restaurant (italian, french, etc)
    # returns None if it's not a restaurant or we cant figure it out
    venue_type = str(venue.get('type', '')).lower()

    # Check primary type first (most specific)
    cuisines = ['italian', 'french', 'japanese', 'chinese', 'vietnamese', 'thai',
                'indian', 'mexican', 'korean', 'greek', 'mediterranean', 'american',
                'pizza', 'sushi', 'ramen', 'pho', 'burger', 'steak', 'seafood',
                'bbq', 'brazilian', 'spanish', 'german', 'turkish', 'lebanese']

    for cuisine in cuisines:
        if cuisine in venue_type:
            return cuisine

    # Fall back to all_types only if not found in primary type
    all_types = str(venue.get('all_types', '')).lower()
    for cuisine in cuisines:
        if cuisine in all_types:
            return cuisine

    return None


def _check_bool_column(venue, col):
    # helper to check boolean columns in the csv (handles True, 'true', 'True', etc)
    val = venue.get(col)
    if val is True:
        return True
    if isinstance(val, str) and val.lower() == 'true':
        return True
    return False


def venue_matches_type(venue, target_type):
    # checks if a venue matches what the user asked for
    # returns True if target appears in venue's type info or name
    # also checks related terms and the serves_*/good_for_* columns
    if not target_type:
        return False

    # Handle case where target_type might be a tuple or list
    if isinstance(target_type, (list, tuple)):
        target_type = target_type[0] if target_type else ''

    target = str(target_type).lower().strip()
    venue_type = str(venue.get('type', '')).lower()
    all_types = str(venue.get('all_types', '')).lower()
    name = str(venue.get('name', '')).lower()
    display = str(venue.get('primary_type_display_name', '')).lower()

    searchable = f"{venue_type} {all_types} {name} {display}"

    # Direct match
    if target in searchable:
        return True

    # Check serves_* and good_for_* columns
    # Maps user-friendly terms to CSV column names
    column_mapping = {
        # Meal types
        'dinner': 'serves_dinner',
        'lunch': 'serves_lunch',
        'breakfast': 'serves_breakfast',
        'brunch': 'serves_brunch',
        'coffee': 'serves_coffee',
        'dessert': 'serves_dessert',
        'beer': 'serves_beer',
        'wine': 'serves_wine',
        'cocktails': 'serves_cocktails',
        'vegetarian': 'serves_vegetarian',
        'veggie': 'serves_vegetarian',
        # Venue features
        'groups': 'good_for_groups',
        'group': 'good_for_groups',
        'kids': 'good_for_children',
        'children': 'good_for_children',
        'family': 'good_for_children',
        'sports': 'good_for_watching_sports',
        'live music': 'live_music',
        'music': 'live_music',
        'outdoor': 'outdoor_seating',
        'patio': 'outdoor_seating',
        'dog-friendly': 'allows_dogs',
        'dogs': 'allows_dogs',
        'pet-friendly': 'allows_dogs',
        'reservable': 'reservable',
        'reservation': 'reservable',
        'takeout': 'takeout',
        'delivery': 'delivery',
        'dine-in': 'dine_in',
    }
    if target in column_mapping:
        col = column_mapping[target]
        if _check_bool_column(venue, col):
            return True

    # Partial match for cuisine names (italia -> italian, etc.)
    # This handles "Ciao Italia" matching "italian"
    if target.endswith('ian') or target.endswith('ese') or target.endswith('ish'):
        # Try root form: italian -> ital, japanese -> japan
        root = target[:-3] if target.endswith('ese') else target[:-2] if target.endswith('an') else target[:-3]
        if len(root) >= 4 and root in searchable:
            return True

    # Also check if venue name contains a form of the target
    # e.g., "italia" in name should match "italian" target
    if target.startswith('ital') and 'ital' in name:
        return True
    if target.startswith('french') and ('french' in name or 'france' in name or 'paris' in name):
        return True
    if target.startswith('japan') and ('japan' in name or 'tokyo' in name):
        return True

    # Check related terms
    related = RELATED_TERMS.get(target, [])
    for rel in related:
        if rel in searchable:
            return True

    return False


def get_venue_features(venue):
    # extracts boolean features from the csv columns
    # useful for scoring venues based on their attributes
    return {
        'good_for_groups': _check_bool_column(venue, 'good_for_groups'),
        'good_for_children': _check_bool_column(venue, 'good_for_children'),
        'good_for_sports': _check_bool_column(venue, 'good_for_watching_sports'),
        'live_music': _check_bool_column(venue, 'live_music'),
        'outdoor_seating': _check_bool_column(venue, 'outdoor_seating'),
        'allows_dogs': _check_bool_column(venue, 'allows_dogs'),
        'reservable': _check_bool_column(venue, 'reservable'),
        'serves_vegetarian': _check_bool_column(venue, 'serves_vegetarian'),
        'takeout': _check_bool_column(venue, 'takeout'),
        'delivery': _check_bool_column(venue, 'delivery'),
        'dine_in': _check_bool_column(venue, 'dine_in'),
    }


# Slot to stage number (for ordering dates)
SLOT_STAGE = {
    'activity': 1,
    'coffee': 2,
    'meal': 3,
    'drinks': 4,
    'dessert': 5,
    'other': 3  # default to meal position
}


# type -> vibe mappings learned from data
LEARNED_TYPE_VIBES = {}


def learn_vibes_from_data(df):
    # learns which vibes go with which venue types from the data
    # e.g. if most bars are labeled 'casual', we learn that connection
    # way better than hardcoding all this stuff
    global LEARNED_TYPE_VIBES

    if df is None or 'type' not in df.columns or 'true_vibe' not in df.columns:
        return

    from collections import Counter

    # group venues by type and count vibes
    for venue_type in df['type'].dropna().unique():
        type_venues = df[df['type'] == venue_type]

        # collect all vibes for this type
        all_vibes = []
        for vibes_str in type_venues['true_vibe'].dropna():
            vibes = [v.strip().lower() for v in str(vibes_str).split(',')]
            all_vibes.extend(vibes)

        if all_vibes:
            # count frequency of each vibe
            vibe_counts = Counter(all_vibes)
            # keep vibes that appear in at least 20% of venues of this type
            threshold = len(type_venues) * 0.2
            common_vibes = [v for v, count in vibe_counts.items() if count >= threshold]

            if common_vibes:
                LEARNED_TYPE_VIBES[venue_type.lower()] = common_vibes


def initialize_from_data(df=None):
    # sets up all the learned mappings from venue data
    # call this once at startup with your dataframe
    # if no df given, tries to load from ottawa_venues.csv
    global _DATA_LEARNED

    if _DATA_LEARNED:
        return  # already done

    if df is None:
        try:
            df = pd.read_csv('ottawa_venues.csv')
        except FileNotFoundError:
            _DATA_LEARNED = True
            return

    learn_vibes_from_data(df)
    learn_related_terms_from_data(df)
    _DATA_LEARNED = True


def get_vibes_for_type(venue_type):
    # gets likely vibes for a venue type based on what we learned from data
    if not venue_type:
        return []

    type_lower = str(venue_type).lower()

    # check exact match first
    if type_lower in LEARNED_TYPE_VIBES:
        return LEARNED_TYPE_VIBES[type_lower]

    # check partial matches
    for known_type, vibes in LEARNED_TYPE_VIBES.items():
        if known_type in type_lower or type_lower in known_type:
            return vibes

    return []


def get_venue_stage(venue):
    # returns the date stage (1-5) for a venue based on what kind of place it is
    slot = get_venue_slot(venue)
    return SLOT_STAGE.get(slot, 3)  # default to meal stage


def sort_by_date_sequence(itinerary):
    # sorts venues into a logical date order (activity -> meal -> drinks -> dessert)
    if not itinerary:
        return itinerary

    # add stage to each venue, then sort
    for v in itinerary:
        v['_stage'] = get_venue_stage(v)

    sorted_plan = sorted(itinerary, key=lambda x: x['_stage'])

    # remove temp field
    for v in sorted_plan:
        del v['_stage']

    return sorted_plan


# related terms - maps words to similar words so "coffee" also matches "cafe" etc
# we learn most of this from data but need some seeds to start
SEED_RELATED_TERMS = {
    # Venues that share the same function
    'coffee': ['cafe', 'café', 'espresso'],
    'cafe': ['coffee', 'café'],
    'bar': ['pub', 'tavern', 'lounge'],
    'pub': ['bar', 'tavern'],
    # Cuisines that have clear synonyms
    'italian': ['trattoria', 'pizzeria', 'ristorante'],
    'pizza': ['pizzeria'],
    'japanese': ['sushi', 'ramen'],
    'sushi': ['japanese'],
    'french': ['bistro', 'brasserie'],
}

# This gets populated from data
LEARNED_RELATED_TERMS = {}

# Combined (seed + learned)
RELATED_TERMS = SEED_RELATED_TERMS.copy()


def learn_related_terms_from_data(df=None):
    # learns related terms by looking at what words appear together in venue data
    # if two type words often show up together theyre probably related
    # like coffee and cafe - makes sense theyd go together
    # important: we filter out generic words that would match everything
    global LEARNED_RELATED_TERMS, RELATED_TERMS

    if df is None:
        try:
            df = pd.read_csv('ottawa_venues.csv')
        except FileNotFoundError:
            return

    from collections import defaultdict

    # BLACKLIST: Generic terms that would match too many venues
    # These should NEVER be learned as related terms
    blacklist = {
        'restaurant', 'food', 'establishment', 'point', 'interest',
        'store', 'shop', 'place', 'service', 'the', 'and', 'bar',
        'cafe', 'ottawa', 'canada', 'ontario'
    }

    # Count co-occurrences of words in venue type fields
    cooccurrence = defaultdict(lambda: defaultdict(int))

    for _, row in df.iterrows():
        # Only use the primary type field for learning (not all_types which has generic stuff)
        type_text = str(row.get('type', '')).lower().replace('_', ' ')

        # Get all words (filter blacklist and short words)
        words = [w.strip() for w in type_text.split()
                 if len(w.strip()) >= 4 and w.strip() not in blacklist]
        unique_words = list(set(words))

        # Count co-occurrences
        for i, w1 in enumerate(unique_words):
            for w2 in unique_words[i+1:]:
                cooccurrence[w1][w2] += 1
                cooccurrence[w2][w1] += 1

    # Build related terms from high co-occurrences
    for word, related in cooccurrence.items():
        # Skip blacklisted words
        if word in blacklist:
            continue
        # Get words that co-occur at least 3 times (also filter blacklist)
        strong_relations = [w for w, count in related.items()
                           if count >= 3 and w not in blacklist]
        if strong_relations:
            LEARNED_RELATED_TERMS[word] = strong_relations[:5]  # Top 5

    # Only merge seed terms - don't add learned terms for cuisine keywords
    # This prevents "italian" from getting "restaurant" added
    RELATED_TERMS.clear()
    RELATED_TERMS.update(SEED_RELATED_TERMS)


def haversine_distance(lat1, lon1, lat2, lon2):
    # calculates distance between two lat/lon points using the haversine formula
    # returns distance in km - this is the "as the crow flies" distance not driving distance

    R = 6371  # earth radius in km

    # convert to radians for the trig functions
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    # the haversine formula - dont ask me to explain the math
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def is_open_now(hours_json, current_dt=None):
    # checks if a venue is open right now based on its hours from google places
    # returns True if open, False if closed
    # if we cant figure it out we just assume its open (better to show it than hide it)

    if not hours_json or pd.isna(hours_json):
        return True  # no data = assume open

    if current_dt is None:
        current_dt = datetime.now()

    try:
        hours_data = json.loads(hours_json)
        periods = hours_data.get('periods', [])

        if not periods:
            return True  # no periods means probably always open?

        # google uses different day numbering than python
        # google: 0=Sunday, 1=Monday, ... 6=Saturday
        # python: 0=Monday, ... 6=Sunday
        py_weekday = current_dt.weekday()
        google_day = (py_weekday + 1) % 7  # convert python day to google day

        current_hour = current_dt.hour
        current_minute = current_dt.minute
        # combine hour and minute into one number for easy comparison (like 1430 for 2:30pm)
        current_time_val = current_hour * 100 + current_minute

        for period in periods:
            open_day = period['open']['day']
            open_time = period['open']['hour'] * 100 + period['open']['minute']

            if 'close' in period:
                close_day = period['close']['day']
                close_time = period['close']['hour'] * 100 + period['close']['minute']

                # normal case - opens and closes on same day
                if open_day == google_day and close_day == google_day:
                    if open_time <= current_time_val < close_time:
                        return True

                # spans midnight - started today ends tomorrow (like a bar open til 2am)
                elif open_day == google_day and close_day == (google_day + 1) % 7:
                    if current_time_val >= open_time:
                        return True

                # spans midnight - started yesterday ends today
                elif open_day == (google_day - 1) % 7 and close_day == google_day:
                    if current_time_val < close_time:
                        return True
            else:
                # no close time usually means 24/7 like a convenience store
                if open_day == 0 and open_time == 0:
                    return True

        return False

    except Exception:
        return True  # if anything goes wrong just say its open


def add_similarity_scores(df, target_types, target_vibes, related_terms=None):
    # adds a similarity_score column to the dataframe based on how well each venue
    # matches what the user asked for. uses vectorized pandas ops so its fast

    if related_terms is None:
        related_terms = RELATED_TERMS

    # build one big searchable text column so we only have to do this once
    # combines type, all_types, display name, and venue name
    df['_search_text'] = (
        df['type'].fillna('').str.replace('_', ' ') + ' ' +
        df['all_types'].fillna('').str.replace('_', ' ') + ' ' +
        df['primary_type_display_name'].fillna('') + ' ' +
        df['name'].fillna('')
    ).str.lower()

    df['similarity_score'] = 0.0

    # check for type matches - give points if the venue matches requested types
    if target_types:
        for t in target_types:
            t_lower = t.lower()
            # direct match gets 2 points
            mask = df['_search_text'].str.contains(t_lower, regex=False)
            df.loc[mask, 'similarity_score'] += 2.0

            # related terms get 1.5 points (like cafe when they said coffee)
            if t_lower in related_terms:
                for rel in related_terms[t_lower]:
                    rel_mask = df['_search_text'].str.contains(rel, regex=False)
                    df.loc[rel_mask, 'similarity_score'] += 1.5

    # also check vibes - smaller bonus for matching vibes
    if target_vibes:
        vibe_col = df['true_vibe'].fillna('').str.lower()
        for v in target_vibes:
            mask = vibe_col.str.contains(v.lower(), regex=False)
            df.loc[mask, 'similarity_score'] += 0.5

    return df


# time-based preferences - what venue types make sense at different times of day
TIME_PREFERENCES = {
    'morning': {  # 6am to 11am
        'preferred': ['cafe', 'coffee', 'bakery', 'breakfast', 'brunch', 'park'],
        'avoid': ['bar', 'pub', 'nightclub', 'club'],
        'boost': 1.5
    },
    'lunch': {  # 11am to 2pm
        'preferred': ['restaurant', 'cafe', 'bistro', 'deli', 'food'],
        'avoid': ['nightclub', 'club'],
        'boost': 1.3
    },
    'afternoon': {  # 2pm to 5pm
        'preferred': ['museum', 'gallery', 'park', 'shopping', 'cafe', 'dessert'],
        'avoid': ['nightclub', 'club'],
        'boost': 1.2
    },
    'evening': {  # 5pm to 9pm - dinner time
        'preferred': ['restaurant', 'dinner', 'italian', 'french', 'steakhouse'],
        'avoid': [],
        'boost': 1.4
    },
    'night': {  # 9pm to 6am
        'preferred': ['bar', 'pub', 'lounge', 'cocktail', 'nightclub', 'club'],
        'avoid': ['cafe', 'breakfast', 'brunch'],
        'boost': 1.5
    }
}


def get_time_period(hour):
    # takes an hour (0-23) and returns what part of day it is
    # used to figure out what venues make sense for that time

    if 6 <= hour < 11:
        return 'morning'
    elif 11 <= hour < 14:
        return 'lunch'
    elif 14 <= hour < 17:
        return 'afternoon'
    elif 17 <= hour < 21:
        return 'evening'
    else:
        return 'night'


def get_time_score_adjustment(venue_type, hour):
    # returns a multiplier for the venue score based on time of day
    # if its a good fit for the time, boost it (>1.0)
    # if its a bad fit, penalize it (<1.0)
    # neutral venues get 1.0 (no change)

    period = get_time_period(hour)
    prefs = TIME_PREFERENCES.get(period, {})

    venue_type_lower = str(venue_type).lower()

    # check if this venue type is preferred for this time
    for pref in prefs.get('preferred', []):
        if pref in venue_type_lower:
            return prefs.get('boost', 1.2)

    # check if we should avoid this venue type at this time
    for avoid in prefs.get('avoid', []):
        if avoid in venue_type_lower:
            return 0.5  # cut the score in half

    return 1.0  # neutral - no adjustment


def suggest_itinerary_order(venues, start_hour):
    # tries to reorder the venues so they make sense for the time
    # like put coffee first if its morning, dinner spots later in evening
    # this is kind of a greedy approach - not guaranteed optimal but works ok

    if len(venues) <= 1:
        return venues

    # assume each venue takes about 2 hours
    hours_per_venue = 2

    scored_orders = []

    # score each venue for each possible position
    for i, venue in enumerate(venues):
        estimated_hour = (start_hour + i * hours_per_venue) % 24
        venue_type = venue.get('type', '') or venue.get('primary_type_display_name', '')
        score = get_time_score_adjustment(venue_type, estimated_hour)
        scored_orders.append((i, venue, score))

    # sort by score so we handle best fits first
    scored_orders.sort(key=lambda x: x[2], reverse=True)

    # now assign each venue to its best available position
    result = [None] * len(venues)
    used_positions = set()

    for orig_idx, venue, score in scored_orders:
        best_pos = None
        best_score = -1

        # find the best position thats not taken yet
        for pos in range(len(venues)):
            if pos in used_positions:
                continue
            estimated_hour = (start_hour + pos * hours_per_venue) % 24
            venue_type = venue.get('type', '') or venue.get('primary_type_display_name', '')
            pos_score = get_time_score_adjustment(venue_type, estimated_hour)
            if pos_score > best_score:
                best_score = pos_score
                best_pos = pos

        if best_pos is not None:
            result[best_pos] = venue
            used_positions.add(best_pos)

    # fill any gaps (shouldnt happen but just in case)
    remaining = [v for v in venues if v not in result]
    for i, v in enumerate(result):
        if v is None and remaining:
            result[i] = remaining.pop(0)

    return result


# Global vibe mappings learned from data
_vibe_mappings = {}

def initialize_from_data(df):
    """
    Learn vibe mappings from data
    Builds statistics for each vibe
    """
    global _vibe_mappings

    if df.empty or 'vibe' not in df.columns:
        return

    # Build vibe mappings from data
    for vibe in df['vibe'].unique():
        vibe_venues = df[df['vibe'] == vibe]
        _vibe_mappings[vibe] = {
            'count': len(vibe_venues),
            'avg_rating': vibe_venues['rating'].mean() if 'rating' in vibe_venues.columns else 0,
            'avg_price': vibe_venues['price_level'].mean() if 'price_level' in vibe_venues.columns else 0
        }


def get_vibe_stats(vibe):
    """Get statistics for a vibe"""
    return _vibe_mappings.get(vibe, {})

