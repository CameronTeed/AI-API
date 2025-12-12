# fetch_real_data.py
# fetches venue data from the google places API
# run this to populate/update the csv with real ottawa venues

import requests
import pandas as pd
import time
import os
import json
import nlp_classifier
from dotenv import load_dotenv

# api key from environment variable - keeps it secure
load_dotenv()
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
OUTPUT_FILE = "ottawa_venues.csv"

# search queries to get a diverse set of venues
# covers restaurants, bars, activities, nature spots
# the more queries we have the better variety of venues we get
SEARCH_QUERIES = [
    # dining - general
    "romantic restaurants in Ottawa",
    "candlelit dinner Ottawa",
    "best dessert spots in Ottawa",
    "late night food Ottawa",
    "fine dining Ottawa",
    "best restaurants downtown Ottawa",
    "hidden gem restaurants Ottawa",
    "cheap eats Ottawa",
    "best brunch spots Ottawa",
    "breakfast restaurants Ottawa",

    # restaurants by cuisine
    "italian restaurants Ottawa",
    "french restaurants Ottawa",
    "japanese restaurants Ottawa",
    "sushi restaurants Ottawa",
    "thai restaurants Ottawa",
    "indian restaurants Ottawa",
    "mexican restaurants Ottawa",
    "greek restaurants Ottawa",
    "vietnamese restaurants Ottawa",
    "korean restaurants Ottawa",
    "chinese restaurants Ottawa",
    "mediterranean restaurants Ottawa",
    "middle eastern food Ottawa",
    "lebanese restaurants Ottawa",
    "steakhouse Ottawa",
    "seafood restaurants Ottawa",
    "vegetarian restaurants Ottawa",
    "vegan restaurants Ottawa",
    "pizza restaurants Ottawa",
    "burger restaurants Ottawa",
    "ramen shops Ottawa",
    "pho restaurants Ottawa",
    "tapas restaurants Ottawa",
    "spanish restaurants Ottawa",

    # cafes and coffee
    "cozy cafes for dates in Ottawa",
    "best coffee shops Ottawa",
    "hipster cafes Ottawa",
    "aesthetic cafes Ottawa",
    "study cafes Ottawa",
    "cafes with good wifi Ottawa",
    "specialty coffee Ottawa",
    "french bakery Ottawa",
    "pastry shops Ottawa",
    "dessert cafes Ottawa",
    "tea houses Ottawa",
    "bubble tea Ottawa",
    "cat cafe Ottawa",
    "brunch cafes Ottawa",

    # nightlife and bars
    "speakeasy bars Ottawa",
    "cocktail bars with live music Ottawa",
    "wine bars in Ottawa",
    "unique pubs in Ottawa",
    "rooftop bars Ottawa",
    "jazz bars Ottawa",
    "craft beer bars Ottawa",
    "sports bars Ottawa",
    "karaoke bars Ottawa",
    "dance clubs Ottawa",
    "lgbtq bars Ottawa",
    "whiskey bars Ottawa",
    "tiki bars Ottawa",
    "irish pubs Ottawa",

    # date activities
    "fun couples activities Ottawa",
    "board game cafes Ottawa",
    "escape rooms Ottawa",
    "comedy clubs Ottawa",
    "interactive museums Ottawa",
    "pottery or painting workshops Ottawa",
    "bowling alleys Ottawa",
    "arcade bars Ottawa",
    "axe throwing Ottawa",
    "mini golf Ottawa",
    "laser tag Ottawa",
    "trampoline parks Ottawa",
    "rock climbing gym Ottawa",
    "dance classes Ottawa",
    "cooking classes Ottawa",
    "wine tasting Ottawa",
    "brewery tours Ottawa",
    "movie theaters Ottawa",
    "drive in theater Ottawa",
    "spa and wellness Ottawa",
    "couples massage Ottawa",
    "yoga studios Ottawa",
    "art galleries Ottawa",
    "live music venues Ottawa",
    "concert halls Ottawa",
    "theater performances Ottawa",
    "stand up comedy Ottawa",

    # outdoors and nature
    "scenic lookouts in Ottawa",
    "beautiful parks for picnics Ottawa",
    "skating rinks in Ottawa",
    "romantic walking trails Ottawa",
    "hidden gems Ottawa",
    "botanical gardens Ottawa",
    "waterfront restaurants Ottawa",
    "patio dining Ottawa",
    "rooftop patios Ottawa",
    "canal side restaurants Ottawa",
    "gatineau park activities",
    "bike rentals Ottawa",
    "kayak rentals Ottawa",
    "beach near Ottawa",

    # neighborhoods - to get local spots
    "best restaurants Byward Market",
    "cafes in Glebe Ottawa",
    "restaurants in Westboro Ottawa",
    "Little Italy Ottawa restaurants",
    "Hintonburg cafes Ottawa",
    "Elgin Street restaurants Ottawa",
    "Centretown restaurants Ottawa",
    "Old Ottawa South cafes",
    "Lansdowne restaurants Ottawa",
    "Bank Street restaurants Ottawa",
]

# google places api endpoint
URL = "https://places.googleapis.com/v1/places:searchText"

# fields we want from the api - more fields = more cost
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.shortFormattedAddress",
    "places.location",
    "places.rating",
    "places.userRatingCount",
    "places.priceLevel",
    "places.priceRange",
    "places.types",
    "places.primaryType",
    "places.primaryTypeDisplayName",
    "places.googleMapsUri",
    "places.websiteUri",
    "places.regularOpeningHours",
    "places.currentOpeningHours",
    "places.editorialSummary",
    "places.reviews",
    "places.generativeSummary",
    "places.reviewSummary",
    "places.neighborhoodSummary",
    "places.servesDessert",
    "places.servesCoffee",
    "places.servesBeer",
    "places.servesWine",
    "places.servesCocktails",
    "places.servesVegetarianFood",
    "places.servesBreakfast",
    "places.servesBrunch",
    "places.servesLunch",
    "places.servesDinner",
    "places.goodForGroups",
    "places.goodForChildren",
    "places.goodForWatchingSports",
    "places.liveMusic",
    "places.outdoorSeating",
    "places.allowsDogs",
    "places.reservable",
    "places.takeout",
    "places.delivery",
    "places.dineIn",
])

def _bool_field(place: dict, key: str) -> bool:
    # safely get a boolean field, returns False if missing
    return bool(place.get(key))

def _json_or_empty(value) -> str:
    # converts nested objects to json strings for csv storage
    # returns empty string if value is None or conversion fails
    if not value:
        return ""
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return ""

def fetch_places(query: str, api_key: str):
    # fetches places from google places api for a search query
    # returns list of venue dictionaries

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }

    payload = {
        "textQuery": query,
        "pageSize": 20,  # Max results per page
        "languageCode": "en",
        "regionCode": "CA", # Restrict to Canada to avoid ambiguity
    }

    print(f"Searching for: '{query}'...")

    try:
        response = requests.post(URL, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            results = data.get("places", [])
            all_places = []

            for place in results:
                location = place.get("location") or {}
                types = place.get("types") or []

                # Prioritize AI-generated summaries, then editorial, then fallback
                gen_summary = (place.get("generativeSummary") or {}).get("overview", {}).get("text")
                editorial_summary = (place.get("editorialSummary") or {}).get("text")

                if gen_summary:
                    description = f"[AI Summary] {gen_summary}"
                elif editorial_summary:
                    description = editorial_summary
                else:
                    description = "No description available."

                # Get the first user review as a sample
                reviews = place.get("reviews") or []
                review = reviews[0].get("text", {}).get("text", "No review available.") if reviews else "No review available."

                # Flatten the data structure for CSV storage
                venue = {
                    "id": place.get("id"),
                    "name": (place.get("displayName") or {}).get("text"),
                    "address": place.get("formattedAddress"),
                    "short_address": place.get("shortFormattedAddress"),
                    "lat": location.get("latitude"),
                    "lon": location.get("longitude"),
                    "rating": place.get("rating", 0),
                    "reviews_count": place.get("userRatingCount", 0),
                    "price_level": str(place.get("priceLevel", "PRICE_LEVEL_UNSPECIFIED")),
                    "price_range": place.get("priceRange"),
                    "primary_type": place.get("primaryType"),
                    "primary_type_display_name": (place.get("primaryTypeDisplayName") or {}).get("text"),
                    "all_types": "|".join(types) if types else "",
                    "type": types[0] if types else "unknown",
                    "google_maps_uri": place.get("googleMapsUri"),
                    "website_uri": place.get("websiteUri"),
                    "regular_opening_hours": _json_or_empty(place.get("regularOpeningHours")),
                    "current_opening_hours": _json_or_empty(place.get("currentOpeningHours")),
                    "description": description,
                    "review": review,
                    "review_summary": (place.get("reviewSummary") or {}).get("text"),
                    "neighborhood_summary": (place.get("neighborhoodSummary") or {}).get("text"),
                    "serves_dessert": _bool_field(place, "servesDessert"),
                    "serves_coffee": _bool_field(place, "servesCoffee"),
                    "serves_beer": _bool_field(place, "servesBeer"),
                    "serves_wine": _bool_field(place, "servesWine"),
                    "serves_cocktails": _bool_field(place, "servesCocktails"),
                    "serves_vegetarian": _bool_field(place, "servesVegetarianFood"),
                    "serves_breakfast": _bool_field(place, "servesBreakfast"),
                    "serves_brunch": _bool_field(place, "servesBrunch"),
                    "serves_lunch": _bool_field(place, "servesLunch"),
                    "serves_dinner": _bool_field(place, "servesDinner"),
                    "good_for_groups": _bool_field(place, "goodForGroups"),
                    "good_for_children": _bool_field(place, "goodForChildren"),
                    "good_for_watching_sports": _bool_field(place, "goodForWatchingSports"),
                    "live_music": _bool_field(place, "liveMusic"),
                    "outdoor_seating": _bool_field(place, "outdoorSeating"),
                    "allows_dogs": _bool_field(place, "allowsDogs"),
                    "reservable": _bool_field(place, "reservable"),
                    "takeout": _bool_field(place, "takeout"),
                    "delivery": _bool_field(place, "delivery"),
                    "dine_in": _bool_field(place, "dineIn"),
                    "true_vibe": "", # Placeholder, will be filled later
                }
                all_places.append(venue)

            print(f"   -> Found {len(results)} places.")
            return all_places

        else:
            print(f"   -> Error: {response.status_code}")
            return []

    except Exception as e:
        print(f"   -> Exception occurred: {e}")
        return []

def fetch_and_save_data(api_key: str, output_file: str = OUTPUT_FILE):
    # main function - fetches all queries and saves to csv
    # handles deduplication so we dont add the same venue twice

    master_list = []
    seen_ids = set()

    # load existing data if we have it
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_csv(output_file)
            seen_ids = set(existing_df["id"].dropna().tolist())
            print(f"Loaded {len(seen_ids)} existing venues. Skipping duplicates.")
            master_list = existing_df.to_dict("records")
        except Exception as e:
            print(f"Warning: Could not read existing file: {e}")

    # fetch new data from each search query
    for q in SEARCH_QUERIES:
        places = fetch_places(q, api_key)
        new_count = 0
        for p in places:
            if p["id"] not in seen_ids:
                master_list.append(p)
                seen_ids.add(p["id"])
                new_count += 1
        print(f"   -> Added {new_count} new unique venues.")
        time.sleep(1)  # dont hit api rate limits

    df = pd.DataFrame(master_list)
    if df.empty:
        print("No data found.")
        return False

    # convert price levels to actual dollar amounts
    price_map = {
        "PRICE_LEVEL_FREE": 0,
        "PRICE_LEVEL_INEXPENSIVE": 15,
        "PRICE_LEVEL_MODERATE": 40,
        "PRICE_LEVEL_EXPENSIVE": 80,
        "PRICE_LEVEL_VERY_EXPENSIVE": 120,
        "PRICE_LEVEL_UNSPECIFIED": 30,
    }
    df["price_level"] = df["price_level"].astype(str)

    if "cost" not in df.columns:
        df["cost"] = df["price_level"].map(price_map).fillna(30)
    else:
        df["cost"] = df["cost"].fillna(df["price_level"].map(price_map))

    # auto-label vibes using the nlp classifier
    print("Auto-labeling new data with NLP Classifier...")

    def get_vibe(row):
        # combine all text for context
        text = f"{str(row.get('description', ''))} {str(row.get('review', ''))} {str(row.get('type', ''))} {str(row.get('name', ''))} {str(row.get('primary_type_display_name', ''))}"

        vibes = nlp_classifier.get_keyword_vibes(text)

        if not vibes:
            return 'casual'

        return ", ".join(vibes)

    df['true_vibe'] = df.apply(get_vibe, axis=1)

    df.to_csv(output_file, index=False)
    print(f"\nSuccess! Total dataset size: {len(df)} venues.")
    print(f"Saved to: {output_file}")
    return True

if __name__ == "__main__":
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        print("Please set the GOOGLE_PLACES_API_KEY environment variable.")
    else:
        fetch_and_save_data(API_KEY)
