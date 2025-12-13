"""
Tool definitions for the LLM Engine.
"""

TOOLS_DEFINITION = [
    # === DATABASE/VECTOR SEARCH TOOLS ===
    {
        "type": "function",
        "function": {
            "name": "search_date_ideas",
            "description": "Search the vector knowledge base for date ideas using semantic similarity and filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query describing the desired date idea"},
                    "city": {"type": "string", "description": "City to filter by"},
                    "max_price_tier": {"type": "integer", "enum": [1, 2, 3], "description": "Maximum price tier (1=budget, 2=moderate, 3=expensive)"},
                    "indoor": {"type": "boolean", "description": "Whether the activity should be indoors"},
                    "categories": {"type": "array", "items": {"type": "string"}, "description": "Categories to filter by (e.g., romantic, outdoor, food)"},
                    "min_duration": {"type": "integer", "description": "Minimum duration in minutes"},
                    "max_duration": {"type": "integer", "description": "Maximum duration in minutes"},
                    "top_k": {"type": "integer", "default": 10, "description": "Number of results to return"}
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_featured_dates",
            "description": "Search for featured, unique, or special date ideas in the database with high quality filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City to search in"},
                    "category": {"type": "string", "description": "Specific category of featured dates (romantic, adventure, cultural, etc.)"}
                },
                "additionalProperties": False
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "find_nearby_venues",
            "description": "Find venues near a specific lat/lng coordinate using Google Places.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude coordinate"},
                    "lon": {"type": "number", "description": "Longitude coordinate"},
                    "venue_type": {"type": "string", "description": "Type of venue (restaurant, entertainment, museum, etc.)", "default": "restaurant"},
                    "radius_km": {"type": "number", "description": "Search radius in kilometers", "default": 5.0}
                },
                "required": ["lat", "lon"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_directions",
            "description": "Get directions and travel information between two locations using Google Maps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Starting location (address or place name)"},
                    "destination": {"type": "string", "description": "Destination location (address or place name)"},
                    "mode": {"type": "string", "enum": ["driving", "walking", "transit", "bicycling"], "default": "driving", "description": "Transportation mode"}
                },
                "required": ["origin", "destination"],
                "additionalProperties": False
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "enhanced_web_search",
            "description": "Enhanced web search with specialized result types for venues and events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "city": {"type": "string", "description": "City to focus search on"},
                    "result_type": {"type": "string", "enum": ["general", "events", "reviews", "deals", "hours"], "default": "general", "description": "Type of information to focus on"}
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    },
    
    # === GEOLOCATION TOOLS ===
    {
        "type": "function",
        "function": {
            "name": "geocode_location",
            "description": "Convert an address or place name to latitude/longitude coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "Address or place name to geocode"}
                },
                "required": ["address"],
                "additionalProperties": False
            }
        }
    },
    
    # === LEGACY TOOLS (for backwards compatibility) ===
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Basic web search for venue hours, tickets, or new events. Use enhanced_web_search for better results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "city": {"type": "string"}
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    },

]
