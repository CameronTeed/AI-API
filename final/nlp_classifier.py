# nlp_classifier.py
# handles vibe classification using both ML (logistic regression) and keyword matching
# the ML model is trained on venue descriptions, keywords are a backup
# NOW SUPPORTS POSTGRESQL DATABASE FOR LEARNING AND CACHING

import pandas as pd
import spacy
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import db_manager
import cache_manager
import os

# load spacy model once at startup - this takes a few seconds
nlp = spacy.load("en_core_web_md")

def compute_semantic_similarity(df, query_text):
    # computes how similar a query is to each venue in the dataset
    # uses spacy word vectors - pretty slow for large datasets but works well
    # returns a pandas series of scores from 0 to 1

    query_doc = nlp(query_text.lower())

    # combine all the text fields for each venue
    def get_venue_text(row):
        return f"{row['name']} {row['primary_type_display_name']} {row['description']} {row['review']}".lower()

    # this is slow because were calling nlp() on every row
    # but its fine for datasets under 1000 rows
    scores = df.apply(lambda row: query_doc.similarity(nlp(get_venue_text(row))), axis=1)

    return scores

def train_vibe_classifier(data_source='ottawa_venues.csv'):
    # trains a logistic regression model to predict vibes from text
    # can pass either a csv path, a dataframe, or 'database' to load from PostgreSQL
    # returns the vectorizer and model so we can use them later

    if isinstance(data_source, str):
        if data_source == 'database':
            # Load from PostgreSQL database
            try:
                db_manager.init_db_pool()
                df = db_manager.get_all_venues()
            except Exception as e:
                print(f"Failed to load from database: {e}. Falling back to CSV.")
                df = pd.read_csv('ottawa_venues.csv')
        else:
            # Load from CSV file
            df = pd.read_csv(data_source)
    else:
        df = data_source

    # drop rows without a vibe label - cant train on those
    df = df.dropna(subset=['true_vibe'])

    # fill empty descriptions so we dont get errors
    df['description'] = df['description'].fillna('')

    X = df['description']
    y = df['true_vibe']

    # 80/20 split for train/test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # TF-IDF turns text into numbers the model can understand
    # basically counts how important each word is
    vectorizer = TfidfVectorizer(stop_words='english')
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    # logistic regression - simple but works well for text
    clf = LogisticRegression(max_iter=1000)
    clf.fit(X_train_tfidf, y_train)

    # print out how well the model did
    predictions = clf.predict(X_test_tfidf)
    print("Classifier Performance:")
    print(classification_report(y_test, predictions))

    return vectorizer, clf


# seed keywords to bootstrap the learning - the rest gets learned from data
SEED_VIBE_KEYWORDS = {
    'romantic': ['romantic', 'intimate', 'candlelit', 'date night'],
    'energetic': ['energetic', 'lively', 'party', 'dance', 'music'],
    'cozy': ['cozy', 'warm', 'comfortable', 'quiet', 'relaxing'],
    'fancy': ['fancy', 'upscale', 'elegant', 'fine dining', 'luxurious'],
    'casual': ['casual', 'relaxed', 'laid-back', 'chill', 'easygoing'],
    'hipster': ['hipster', 'trendy', 'artisan', 'craft', 'indie'],
    'historic': ['historic', 'heritage', 'museum', 'landmark', 'history'],
    'outdoors': ['outdoor', 'patio', 'nature', 'park', 'garden'],
    'artsy': ['artsy', 'gallery', 'creative', 'art', 'artistic'],
    'family': ['family', 'kids', 'children', 'family-friendly'],
    'foodie': ['gourmet', 'culinary', 'chef', 'delicious', 'authentic'],
    'scenic': ['scenic', 'view', 'panorama', 'beautiful', 'picturesque'],
    'shopping': ['shop', 'store', 'boutique', 'market', 'retail'],
    'wellness': ['spa', 'yoga', 'massage', 'meditation', 'wellness']
}

# This will be populated by learn_vibe_keywords_from_data()
LEARNED_VIBE_KEYWORDS = {}

# Combined keywords (seed + learned) - this is what gets exported
VIBE_KEYWORDS = SEED_VIBE_KEYWORDS.copy()


def learn_vibe_keywords_from_data(csv_path='ottawa_venues.csv', min_frequency=0.1):
    # learns vibe keywords from the actual venue data instead of hardcoding them
    # for each vibe, finds words that show up a lot in venues with that vibe
    # but less in venues without it
    #
    # this approach is way better than hardcoding because:
    # 1. adapts to whatever data you have
    # 2. finds patterns you might not think of
    # 3. updates automatically when you add new venues
    global LEARNED_VIBE_KEYWORDS, VIBE_KEYWORDS

    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Warning: {csv_path} not found, using seed keywords only")
        return

    if 'true_vibe' not in df.columns or 'description' not in df.columns:
        return

    # Combine text fields for analysis
    df['_text'] = (
        df['description'].fillna('') + ' ' +
        df['review'].fillna('') + ' ' +
        df['name'].fillna('')
    ).str.lower()

    # Get all unique vibes from the data
    all_vibes = set()
    for vibe_str in df['true_vibe'].dropna():
        for v in str(vibe_str).split(','):
            all_vibes.add(v.strip().lower())

    # For each vibe, find characteristic words
    for vibe in all_vibes:
        # Get venues with this vibe
        has_vibe = df['true_vibe'].fillna('').str.lower().str.contains(vibe)
        vibe_texts = ' '.join(df[has_vibe]['_text'].tolist())
        other_texts = ' '.join(df[~has_vibe]['_text'].tolist())

        # Tokenize and count words
        vibe_words = {}
        for word in vibe_texts.split():
            word = word.strip('.,!?;:()[]"\'')
            if len(word) >= 4:  # Skip short words
                vibe_words[word] = vibe_words.get(word, 0) + 1

        other_words = {}
        for word in other_texts.split():
            word = word.strip('.,!?;:()[]"\'')
            if len(word) >= 4:
                other_words[word] = other_words.get(word, 0) + 1

        # Find words that are characteristic of this vibe
        # (appear more often in vibe venues than in others)
        characteristic = []
        total_vibe = sum(vibe_words.values()) or 1
        total_other = sum(other_words.values()) or 1

        for word, count in vibe_words.items():
            if count < 3:  # Must appear at least 3 times
                continue

            vibe_freq = count / total_vibe
            other_freq = other_words.get(word, 0) / total_other

            # Word is characteristic if it appears 2x more often in vibe venues
            if vibe_freq > other_freq * 2 and vibe_freq > min_frequency / 100:
                characteristic.append(word)

        LEARNED_VIBE_KEYWORDS[vibe] = characteristic[:20]  # Top 20 per vibe

    # Merge learned keywords with seed keywords
    for vibe in set(list(SEED_VIBE_KEYWORDS.keys()) + list(LEARNED_VIBE_KEYWORDS.keys())):
        combined = set(SEED_VIBE_KEYWORDS.get(vibe, []))
        combined.update(LEARNED_VIBE_KEYWORDS.get(vibe, []))
        VIBE_KEYWORDS[vibe] = list(combined)

    print(f"  Learned keywords for {len(LEARNED_VIBE_KEYWORDS)} vibes from data")


# Auto-learn on import if data exists
import os
if os.path.exists('ottawa_venues.csv'):
    learn_vibe_keywords_from_data()

# type-based vibe inference - learned from data + minimal seeds
# This maps venue types to their common vibes

# Minimal seed mappings (just the most obvious ones)
SEED_TYPE_VIBE_MAP = {
    'bar': ['casual'],
    'pub': ['casual'],
    'coffee_shop': ['cozy'],
    'cafe': ['cozy'],
    'park': ['outdoors'],
    'museum': ['artsy', 'historic'],
    'spa': ['wellness'],
    'nightclub': ['energetic'],
}

# This gets populated from data
LEARNED_TYPE_VIBE_MAP = {}

# Combined map (seed + learned)
TYPE_VIBE_MAP = SEED_TYPE_VIBE_MAP.copy()


def learn_type_vibe_map_from_data(csv_path='ottawa_venues.csv'):
    # figures out which vibes are common for each venue type by looking at the data
    # e.g. if most bars are labeled 'casual', we learn that association
    global LEARNED_TYPE_VIBE_MAP, TYPE_VIBE_MAP

    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        return

    if 'type' not in df.columns or 'true_vibe' not in df.columns:
        return

    from collections import Counter

    for venue_type in df['type'].dropna().unique():
        type_venues = df[df['type'] == venue_type]

        # Count vibes for this type
        vibe_counts = Counter()
        for vibe_str in type_venues['true_vibe'].dropna():
            for v in str(vibe_str).split(','):
                v = v.strip().lower()
                if v:
                    vibe_counts[v] += 1

        # Keep vibes that appear in at least 20% of venues of this type
        threshold = len(type_venues) * 0.2
        common_vibes = [v for v, count in vibe_counts.items() if count >= max(threshold, 2)]

        if common_vibes:
            type_key = venue_type.lower().replace(' ', '_')
            LEARNED_TYPE_VIBE_MAP[type_key] = common_vibes

    # Merge with seeds
    for t in set(list(SEED_TYPE_VIBE_MAP.keys()) + list(LEARNED_TYPE_VIBE_MAP.keys())):
        combined = set(SEED_TYPE_VIBE_MAP.get(t, []))
        combined.update(LEARNED_TYPE_VIBE_MAP.get(t, []))
        TYPE_VIBE_MAP[t] = list(combined)

    print(f"  Learned type-vibe mappings for {len(LEARNED_TYPE_VIBE_MAP)} venue types")


# Auto-learn on import
if os.path.exists('ottawa_venues.csv'):
    learn_type_vibe_map_from_data()

def get_keyword_vibes(text, venue_type=None, use_learned=True):
    # extracts vibes by matching keywords in the text
    # uses SEED keywords for precise matching
    # optionally uses LEARNED keywords for better recall (venue classification)
    # NOW WITH SMART CACHING to avoid redundant computations

    # Check cache first
    cached_vibes = cache_manager.get_cached_vibe_prediction(text)
    if cached_vibes is not None:
        return cached_vibes

    text = text.lower()
    vibes = set()

    import re

    # Always check SEED keywords (precise matching)
    for vibe, keys in SEED_VIBE_KEYWORDS.items():
        pattern = r'\b(' + '|'.join(map(re.escape, keys)) + r')\b'
        if re.search(pattern, text):
            vibes.add(vibe)

    # If use_learned=True, also check LEARNED keywords
    # This gives better recall for venue classification
    if use_learned and LEARNED_VIBE_KEYWORDS:
        for vibe, keys in LEARNED_VIBE_KEYWORDS.items():
            # Require at least 2 learned keyword matches to reduce false positives
            match_count = 0
            for key in keys:
                if len(key) >= 4:  # Skip short words to reduce noise
                    pattern = r'\b' + re.escape(key) + r'\b'
                    if re.search(pattern, text):
                        match_count += 1
            if match_count >= 2:
                vibes.add(vibe)

    # also check venue type for vibes if we have it
    if venue_type:
        venue_type_lower = venue_type.lower().replace(' ', '_')
        # check exact match first
        if venue_type_lower in TYPE_VIBE_MAP:
            for v in TYPE_VIBE_MAP[venue_type_lower]:
                vibes.add(v)
        else:
            # check partial matches (e.g. "sports_bar" contains "bar")
            for type_key, type_vibes in TYPE_VIBE_MAP.items():
                if type_key in venue_type_lower or venue_type_lower in type_key:
                    for v in type_vibes:
                        vibes.add(v)

    result = list(vibes)

    # Cache the result for future use
    cache_manager.cache_vibe_prediction(text, result)

    return result


def semantic_type_match(venue, target_types, threshold=0.35):
    # fast type matching using substrings and related terms
    # we used to use spacy similarity here but it was way too slow
    # returns (matched_type, score) or (None, 0) if no match

    if not target_types:
        return None, 0

    # combine all the type info into one searchable string
    venue_type = str(venue.get('type', '')).replace('_', ' ')
    venue_all_types = str(venue.get('all_types', '')).replace('_', ' ')
    venue_display = str(venue.get('primary_type_display_name', ''))
    venue_name = str(venue.get('name', ''))

    venue_text = f"{venue_type} {venue_all_types} {venue_display} {venue_name}".lower()

    # Use dynamically learned related terms from planner_utils
    from planner_utils import RELATED_TERMS

    for target in target_types:
        target_lower = target.lower()

        # direct substring match - fastest option
        if target_lower in venue_text:
            return target, 1.0

        # Handle cuisine name variations (italian -> italia, ital)
        # This catches "Ciao Italia" for "italian" query
        if target_lower.startswith('ital') and 'ital' in venue_text:
            return target, 0.95
        if target_lower.startswith('french') and ('french' in venue_text or 'france' in venue_text or 'paris' in venue_text):
            return target, 0.95
        if target_lower.startswith('japan') and ('japan' in venue_text or 'tokyo' in venue_text):
            return target, 0.95

        # check related terms if direct match fails (using learned mappings)
        if target_lower in RELATED_TERMS:
            for related in RELATED_TERMS[target_lower]:
                if related in venue_text:
                    return target, 0.9

    return None, 0


def calculate_venue_similarity(venue, semantic_query, target_vibes=None, target_types=None):
    # scores how well a venue matches what the user wants
    # type matches are weighted highest since thats usually what people care about
    # returns a float score - higher is better

    score = 0.0

    # type matching is most important
    if target_types:
        matched_type, type_score = semantic_type_match(venue, target_types)
        if matched_type:
            score += type_score * 2.0  # big bonus for type match

    # vibe matching
    if target_vibes:
        venue_vibes = [v.strip().lower() for v in str(venue.get('true_vibe', '')).split(',')]
        for tv in target_vibes:
            if tv.lower() in venue_vibes:
                score += 0.3

    # simple keyword matching for anything else
    if semantic_query:
        venue_text = f"{venue.get('name', '')} {venue.get('primary_type_display_name', '')}".lower()
        query_words = semantic_query.lower().split()
        for word in query_words:
            if len(word) > 3 and word in venue_text:
                score += 0.2

    return score

def predict_vibes(text, vectorizer, model):
    # combines ML prediction with keyword matching
    # returns comma-separated string of vibes

    # get ML prediction
    text_vec = vectorizer.transform([text])
    ml_vibe = model.predict(text_vec)[0]

    # also check keywords
    keyword_vibes = get_keyword_vibes(text)

    # combine both
    all_vibes = set(keyword_vibes)
    all_vibes.add(ml_vibe)

    # remove neutral if we have real vibes
    if 'neutral' in all_vibes and len(all_vibes) > 1:
        all_vibes.remove('neutral')

    return ", ".join(list(all_vibes))

# Integration function for AI Orchestrator
def get_keyword_vibes_integration(text):
    """
    Integration wrapper for AI Orchestrator
    Predicts vibes from text using keyword matching
    Returns list of vibes
    """
    try:
        vibes = get_keyword_vibes(text)
        return vibes if vibes else ['casual']
    except Exception as e:
        print(f"Error in vibe prediction: {e}")
        return ['casual']


if __name__ == "__main__":
    # Example usage to predict a new venue's vibe
    try:
        vec, model = train_vibe_classifier()

        new_desc = "A very quiet and dark place with candles, perfect for a date."
        print(f"Predicted Vibes: {predict_vibes(new_desc, vec, model)}")

    except Exception as e:
        print(f"Error: {e}")
