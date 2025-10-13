# Tool Calling Improvements

## Changes Made

### 1. Added Missing Tool Handlers
**Problem:** `scrapingbee_scrape` and `eventbrite_search` tools were defined but not connected in the execution layer.

**Solution:** Added handlers in `server/llm/engine.py`:
```python
elif function_name == "scrapingbee_scrape":
    return await agent_tools.scrapingbee_scrape(**function_args)
elif function_name == "eventbrite_search":
    return await agent_tools.eventbrite_search(**function_args)
```

### 2. Enhanced System Prompt
**Problem:** The system prompt wasn't clear enough about using ALL available tools.

**Solution:** Completely rewrote `server/llm/system_prompt.py`:
- ✅ Lists all 11 available tools with descriptions
- ✅ Provides specific usage patterns for different scenarios
- ✅ Includes concrete examples (romantic dinner, winter activities, live music)
- ✅ Emphasizes using 3-4+ tools per request
- ✅ Forbids single-tool responses

### 3. Improved Multi-Tool Forcing Logic
**Problem:** System only forced additional tools when exactly 1 tool was called.

**Solution:** Enhanced forcing logic in `server/llm/engine.py`:
- Now forces additional tools when **fewer than 3** tools are called
- Ensures these core tools are always considered:
  - `search_date_ideas` (database search)
  - `search_featured_dates` (special content)
  - `google_places_search` (real-time venues)
  - `enhanced_web_search` (current events)
  - `eventbrite_search` (event platform)
- Automatically executes missing tools and adds results to context
- Limits to 3 additional tools to avoid token limits

### 4. Better Tool Argument Handling
**Problem:** Query terms weren't being extracted and formatted properly.

**Solution:** Improved query processing:
- Cleans user queries before passing to tools
- Makes Google Places queries city-specific
- Extracts search terms from natural language
- Passes appropriate result_type to enhanced_web_search

## Available Tools (All 11)

### Database Tools
1. `search_date_ideas` - Semantic search of curated database
2. `search_featured_dates` - Find special/unique experiences

### Real-Time Data Tools
3. `google_places_search` - Find current venues via Google Places API
4. `find_nearby_venues` - Location-based venue discovery
5. `get_directions` - Travel time and routing

### Web Research Tools
6. `enhanced_web_search` - Specialized search (events, reviews, deals, hours)
7. `eventbrite_search` - Event discovery on Eventbrite
8. `web_scrape_venue_info` - Extract venue details from websites
9. `scrapingbee_scrape` - Advanced scraping for JavaScript sites

### Utility Tools
10. `geocode_location` - Address to coordinates conversion
11. `web_search` - Basic web search (legacy/fallback)

## Expected Behavior

### Before Changes
- AI might call only 1 tool (usually just google_places_search)
- Results were limited to single source
- eventbrite_search and scrapingbee_scrape were never called

### After Changes
- AI will call minimum 3-4 tools per request
- System automatically supplements if AI doesn't call enough tools
- Results combine database + Google + web + events
- All 11 tools are now fully functional and accessible

## Testing

To verify tools are working:

1. **Check logs** - Look for "Calling tool X" messages showing multiple tools
2. **Watch for forcing** - Should see "FORCE-CALLING additional tool" when <3 tools called
3. **Verify sources** - Results should show "source": "mixed" or multiple sources
4. **Count tool calls** - Should see 3+ tool executions in logs per request

## Example Log Pattern (Good)

```
🔧 Calling tool 1/3: search_date_ideas with args: {...}
🔧 Calling tool 2/3: google_places_search with args: {...}
🔧 Calling tool 3/3: enhanced_web_search with args: {...}
✅ Successfully executed tool: search_date_ideas
✅ Successfully executed tool: google_places_search
✅ Successfully executed tool: enhanced_web_search
```

Or with forcing:

```
🔧 Calling tool 1/1: google_places_search with args: {...}
🚀 Only 1 tool(s) called - forcing additional comprehensive search
🔧 FORCE-CALLING additional tool: search_date_ideas with args: {...}
🔧 FORCE-CALLING additional tool: enhanced_web_search with args: {...}
🔧 FORCE-CALLING additional tool: eventbrite_search with args: {...}
✅ Successfully executed additional tool: search_date_ideas
✅ Successfully executed additional tool: enhanced_web_search
✅ Successfully executed additional tool: eventbrite_search
```

## Files Modified

- `server/llm/engine.py` - Added missing tool handlers + improved forcing logic
- `server/llm/system_prompt.py` - Complete rewrite with comprehensive tool guidance

## Result

The AI will now use multiple data sources for every request, providing more comprehensive and useful date recommendations!
