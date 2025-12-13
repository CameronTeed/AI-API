"""
Venue Data Fetcher - Retrieves venue details from database

Fetches specific venue information based on question type:
- Database: dietary, accessibility, parking, price, kids, dogs
- Google Places: hours, phone, website
- Web Search: reviews, atmosphere, menu (fallback)
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class VenueDataFetcher:
    """Fetch venue details from database based on question type"""

    def __init__(self, db_connection=None):
        """Initialize with optional database connection"""
        self.db = db_connection

    def fetch_venue_details(
        self,
        venue_ids: List[str],
        question_type: str,
        question: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch venue details from database based on question type

        Args:
            venue_ids: List of venue IDs to fetch
            question_type: Type of question (dietary, hours, etc.)
            question: Original user question

        Returns:
            List of venue details dictionaries
        """
        if not venue_ids:
            return []

        # Map question types to database fields
        field_mapping = {
            "dietary": [
                "name", "address", "serves_vegetarian",
                "serves_breakfast", "serves_lunch", "serves_dinner"
            ],
            "accessibility": [
                "name", "address", "good_for_children", "outdoor_seating"
            ],
            "parking": [
                "name", "address", "outdoor_seating"
            ],
            "price": [
                "name", "address", "cost", "price_level"
            ],
            "kids": [
                "name", "address", "good_for_children", "good_for_groups"
            ],
            "dogs": [
                "name", "address", "allows_dogs", "outdoor_seating"
            ],
            "hours": [
                "name", "address", "website_uri", "google_maps_uri"
            ],
            "phone": [
                "name", "address", "website_uri", "google_maps_uri"
            ],
            "website": [
                "name", "address", "website_uri", "reservable"
            ],
            "reviews": [
                "name", "address", "rating", "reviews_count", "review_summary"
            ],
            "atmosphere": [
                "name", "address", "live_music", "outdoor_seating", "review_summary"
            ],
            "menu": [
                "name", "address", "serves_dessert", "serves_coffee",
                "serves_beer", "serves_wine", "serves_cocktails"
            ],
        }

        # Get fields for this question type
        fields = field_mapping.get(question_type, ["name", "address"])

        # Build query
        try:
            if self.db:
                # Query database for venue details
                placeholders = ",".join(["%s"] * len(venue_ids))
                query = f"""
                    SELECT {", ".join(fields)}
                    FROM venues
                    WHERE id IN ({placeholders})
                    ORDER BY rating DESC
                """

                with self.db.cursor() as cursor:
                    cursor.execute(query, venue_ids)
                    results = cursor.fetchall()

                    # Convert to list of dicts
                    column_names = [desc[0] for desc in cursor.description]
                    venues = [dict(zip(column_names, row)) for row in results]

                logger.info(
                    f"Fetched {len(venues)} venues from database "
                    f"for question type '{question_type}'"
                )
                return venues
            else:
                logger.warning("Database connection not available")
                return []

        except Exception as e:
            logger.error(f"Error fetching venue details: {e}")
            return []

    def format_venue_details(
        self,
        venues: List[Dict[str, Any]],
        question_type: str
    ) -> str:
        """
        Format venue details for OpenAI context

        Args:
            venues: List of venue detail dictionaries
            question_type: Type of question

        Returns:
            Formatted string for OpenAI context
        """
        if not venues:
            return "No venue details available."

        formatted = "Venue Details:\n"

        for venue in venues:
            name = venue.get("name", "Unknown")
            address = venue.get("address", "")
            formatted += f"\n**{name}**\n"

            if address:
                formatted += f"  Address: {address}\n"

            # Add question-specific details
            if question_type == "dietary":
                veg = "✓ Yes" if venue.get("serves_vegetarian") else "✗ No"
                formatted += f"  Vegetarian options: {veg}\n"

            elif question_type == "accessibility":
                kids = "✓ Yes" if venue.get("good_for_children") else "✗ No"
                outdoor = "✓ Yes" if venue.get("outdoor_seating") else "✗ No"
                formatted += f"  Good for children: {kids}\n"
                formatted += f"  Outdoor seating: {outdoor}\n"

            elif question_type == "parking":
                outdoor = "✓ Yes" if venue.get("outdoor_seating") else "✗ No"
                formatted += f"  Outdoor seating: {outdoor}\n"

            elif question_type == "price":
                cost = venue.get("cost", "Unknown")
                level = venue.get("price_level", "")
                formatted += f"  Cost: ${cost} ({level})\n"

            elif question_type == "kids":
                kids = "✓ Yes" if venue.get("good_for_children") else "✗ No"
                groups = "✓ Yes" if venue.get("good_for_groups") else "✗ No"
                formatted += f"  Good for children: {kids}\n"
                formatted += f"  Good for groups: {groups}\n"

            elif question_type == "dogs":
                dogs = "✓ Yes" if venue.get("allows_dogs") else "✗ No"
                outdoor = "✓ Yes" if venue.get("outdoor_seating") else "✗ No"
                formatted += f"  Allows dogs: {dogs}\n"
                formatted += f"  Outdoor seating: {outdoor}\n"

            elif question_type == "reviews":
                rating = venue.get("rating", "N/A")
                count = venue.get("reviews_count", 0)
                summary = venue.get("review_summary", "")
                formatted += f"  Rating: {rating}/5 ({count} reviews)\n"
                if summary:
                    formatted += f"  Summary: {summary}\n"

            elif question_type == "menu":
                items = []
                if venue.get("serves_dessert"):
                    items.append("dessert")
                if venue.get("serves_coffee"):
                    items.append("coffee")
                if venue.get("serves_beer"):
                    items.append("beer")
                if venue.get("serves_wine"):
                    items.append("wine")
                if venue.get("serves_cocktails"):
                    items.append("cocktails")
                if items:
                    formatted += f"  Serves: {', '.join(items)}\n"

        return formatted

