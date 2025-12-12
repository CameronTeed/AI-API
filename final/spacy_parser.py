# spacy_parser.py
# uses spacy NLP to parse user queries and extract planning parameters
# finds things like budget, location, vibes, venue types from natural language

import spacy
from spacy.matcher import Matcher
import pandas as pd
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from nlp_classifier import VIBE_KEYWORDS
except ImportError:
    # fallback if nlp_classifier import fails
    VIBE_KEYWORDS = {}

try:
    from config.scoring_config import ScoringConfig
except ImportError:
    # fallback if config import fails
    ScoringConfig = None

# global model variable - loaded lazily
nlp = None

# these get filled in from the dataset
KNOWN_VIBES = []
KNOWN_TYPES = []
VIBE_SYNONYMS = {}
TYPE_SYNONYMS = {}

# tracks if weve loaded vocab yet
_data_loaded = False


def load_dynamic_vocabulary(csv_path='ottawa_venues.csv'):
    # loads vibes and types from the csv so we dont have to hardcode them
    # this way the parser stays in sync with whatever data we have

    global KNOWN_VIBES, KNOWN_TYPES, VIBE_SYNONYMS, TYPE_SYNONYMS, _data_loaded

    if _data_loaded:
        return

    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)

            # get unique vibes from the true_vibe column
            if 'true_vibe' in df.columns:
                all_vibes = set()
                for vibe_str in df['true_vibe'].dropna().unique():
                    # handle comma-separated vibes like "romantic, cozy"
                    for v in str(vibe_str).split(','):
                        v = v.strip().lower()
                        if v:
                            all_vibes.add(v)
                KNOWN_VIBES = list(all_vibes)

            # get unique types from type columns
            all_types = set()
            for col in ['type', 'primary_type_display_name']:
                if col in df.columns:
                    for t in df[col].dropna().unique():
                        t_normalized = str(t).lower().replace('_', ' ').strip()
                        if t_normalized:
                            all_types.add(t_normalized)
                            # also add individual words for multi-word types
                            for word in t_normalized.split():
                                if len(word) > 2:
                                    all_types.add(word)
            KNOWN_TYPES = list(all_types)

        except Exception:
            pass  # if csv fails just use defaults

    # build vibe synonyms from the classifier keywords
    VIBE_SYNONYMS = {}
    TYPE_SYNONYMS = {}

    for vibe, keywords in VIBE_KEYWORDS.items():
        for keyword in keywords:
            if ' ' not in keyword and len(keyword) >= 3:
                if keyword not in VIBE_SYNONYMS:
                    VIBE_SYNONYMS[keyword] = []
                if vibe not in VIBE_SYNONYMS[keyword]:
                    VIBE_SYNONYMS[keyword].append(vibe)

    _data_loaded = True


def reload_vocabulary(csv_path='ottawa_venues.csv'):
    # force reload the vocab - call after updating the csv
    global _data_loaded
    _data_loaded = False
    load_dynamic_vocabulary(csv_path)


def get_known_vibes():
    # returns list of known vibes, loads if needed
    if not _data_loaded:
        load_dynamic_vocabulary()
    return KNOWN_VIBES


def get_known_types():
    # returns list of known types, loads if needed
    if not _data_loaded:
        load_dynamic_vocabulary()
    return KNOWN_TYPES

def get_nlp_model():
    # loads spacy model lazily - downloads if not installed
    # also initializes the vocabulary from csv

    global nlp
    if nlp is None:
        try:
            nlp = spacy.load("en_core_web_md")
        except OSError:
            from spacy.cli import download
            download("en_core_web_md")
            nlp = spacy.load("en_core_web_md")

        load_dynamic_vocabulary()

    return nlp

def parse_with_spacy(text):
    # main parsing function - takes user query and extracts all the params
    # uses spacy for tokenization and pattern matching
    # returns dict with vibes, budget, location, stops, types

    nlp_model = get_nlp_model()
    doc = nlp_model(text)
    matcher = Matcher(nlp_model.vocab)

    # --- 1. Define Budget Patterns ---
    # We look for patterns like "$150", "under 150", "150 dollars"
    budget_patterns = [
        [{"ORTH": "$"}, {"LIKE_NUM": True}],
        [{"LOWER": "under"}, {"LIKE_NUM": True}],
        [{"LIKE_NUM": True}, {"LOWER": "dollars"}],
        [{"LOWER": "budget"}, {"LOWER": "of"}, {"LIKE_NUM": True}] 
    ]
    matcher.add("BUDGET_PATTERN", budget_patterns)

    # --- 2. Define Stop Count Patterns ---
    # We look for patterns like "3 stops", "5 places", "5 dates"
    # Also allow for intervening words like "5 fun dates"
    stop_patterns = [
        [{"LIKE_NUM": True}, {"LOWER": {"IN": ["stops", "places", "venues", "spots", "locations", "stop", "place", "venue", "spot", "location", "dates", "date"]}}],
        [{"LIKE_NUM": True}, {"IS_ALPHA": True, "OP": "*"}, {"LOWER": {"IN": ["stops", "places", "venues", "spots", "locations", "stop", "place", "venue", "spot", "location", "dates", "date"]}}]
    ]
    matcher.add("STOP_PATTERN", stop_patterns)

    # --- 3. Extract Budget & Stops ---
    # Use dynamic defaults from ScoringConfig if available
    default_budget = ScoringConfig.DEFAULT_BUDGET if ScoringConfig else 150
    default_stops = ScoringConfig.DEFAULT_ITINERARY_LENGTH if ScoringConfig else 3

    detected_budget = default_budget # Default fallback (learned from data)
    detected_stops = default_stops    # Default fallback (learned from data)
    
    matches = matcher(doc)
    
    for match_id, start, end in matches:
        string_id = nlp_model.vocab.strings[match_id]
        span = doc[start:end]
        
        if string_id == "BUDGET_PATTERN":
            for token in span:
                if token.like_num:
                    try:
                        detected_budget = int(token.text)
                    except ValueError:
                        pass
        
        elif string_id == "STOP_PATTERN":
            # The number is usually the first token
            first_token = span[0]
            if first_token.like_num:
                try:
                    val = int(first_token.text)
                    if val > 0 and val <= 10: # Sanity check
                        detected_stops = val
                except ValueError:
                    pass

    # --- 4. Extract Vibe & Type DYNAMICALLY using linguistic analysis ---
    # Uses SpaCy's POS tags, dependency parsing, and semantic similarity
    # NO hardcoded word lists - learns from the data and uses NLP
    detected_vibes = set()
    detected_types = []

    # Get location entities to exclude them from types (using NER)
    location_entities = set()
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC", "FAC"]:  # Places, locations, facilities
            location_entities.add(ent.text.lower())
            # Also add individual words from multi-word locations
            for word in ent.text.lower().split():
                location_entities.add(word)

    # === SIMPLIFIED EXTRACTION ===
    # 1. Types = NOUNs and ADJs (excluding vibes, locations, stop words)
    # 2. Vibes = Dynamically inferred from query using classifier

    # Build set of known vibe words (lowercase)
    known_vibes_lower = {v.lower() for v in KNOWN_VIBES}

    for token in doc:
        lemma = token.lemma_.lower()

        # Skip tokens using SpaCy's built-in linguistic features
        if token.is_stop or token.is_punct or token.is_space:
            continue
        if len(lemma) < 3:
            continue
        if token.like_num or token.pos_ == "NUM":
            continue
        if token.pos_ in ["VERB", "PRON", "DET", "ADP", "CCONJ", "SCONJ", "PART", "SYM"]:
            continue
        if lemma in location_entities:
            continue

        # === TYPE EXTRACTION ===
        # NOUNs and ADJs that aren't vibes
        if token.pos_ in ["NOUN", "PROPN", "ADJ"]:
            # Skip if it's a known vibe word
            if lemma in known_vibes_lower:
                detected_vibes.add(lemma)
                continue

            # Add as type if not already added
            if lemma not in detected_types:
                detected_types.append(lemma)

    # === DYNAMIC VIBE INFERENCE ===
    # Use the classifier to infer vibes from the full query text
    # use_learned=False for query parsing (more precise, fewer false positives)
    try:
        from nlp_classifier import get_keyword_vibes
        inferred_vibes = get_keyword_vibes(text, use_learned=False)
        if inferred_vibes:
            for v in inferred_vibes:
                detected_vibes.add(v)
    except ImportError:
        pass
            
    # --- 5. Extract Location (Named Entity Recognition) ---
    detected_location = "Ottawa" # Default
    for ent in doc.ents:
        if ent.label_ == "GPE": # Geo-Political Entity
            detected_location = ent.text

    # --- 6. Construct Semantic Search Query ---
    # We want to remove the "structural" parts of the query (budget, stops, location)
    # and keep the "content" parts (vibes, activities).
    # This is a heuristic: remove numbers, currency, and the detected location.
    
    search_tokens = []
    for token in doc:
        # Skip budget/stop related tokens (numbers, currency)
        if token.like_num or token.is_currency:
            continue
        # Skip the detected location
        if token.text in detected_location:
            continue
        # Skip stop words/punctuation, but keep important ones?
        # Actually, for semantic search, keeping some structure is okay, 
        # but we definitely want to remove "under $100" or "3 stops".
        if not token.is_punct and not token.is_stop:
            search_tokens.append(token.text)

    semantic_query = " ".join(search_tokens)

    # --- 7. Infer vibes from types if none detected ---
    # Use TYPE_VIBE_MAP learned from data (in nlp_classifier)
    if not detected_vibes and detected_types:
        try:
            from nlp_classifier import TYPE_VIBE_MAP
            for t in detected_types:
                t_lower = t.lower()
                if t_lower in TYPE_VIBE_MAP:
                    for v in TYPE_VIBE_MAP[t_lower]:
                        detected_vibes.add(v)
                    break  # Take first matching type's vibes
        except ImportError:
            pass

    return {
        "target_vibes": list(detected_vibes),
        "budget_limit": detected_budget,
        "location": detected_location,
        "itinerary_length": detected_stops,
        "target_types": detected_types,
        "semantic_query": semantic_query # New field for the planner
    }

# --- Test Block ---
if __name__ == "__main__":
    # Show dynamically loaded vocabulary
    print("=== Dynamic Vocabulary ===")
    print(f"Known Vibes: {get_known_vibes()}")
    print(f"Known Types (sample): {get_known_types()[:10]}...")
    print()

    # Test parsing with the user's query
    queries = [
        "Find me Italian coffee date in ottawa",
        "I am looking for the coziest date in Kanata under 200",
        "Plan a romantic night, budget of $50.",
        "Sushi restaurant with outdoor seating",
        "Fun bars near ByWard Market"
    ]

    for q in queries:
        print(f"Query: '{q}'")
        result = parse_with_spacy(q)
        print(f"  Vibes: {result['target_vibes']}")
        print(f"  Types: {result['target_types']}")
        print(f"  Budget: ${result['budget_limit']}")
        print(f"  Location: {result['location']}")
        print()
