# SerpAPI Integration for Web Search

## Overview

The web scraping system now uses **SerpAPI** (Google Search API) as the primary search engine, with DuckDuckGo as a fallback. This provides significantly better search results for finding blogs, posts, articles, and local content.

## Why SerpAPI?

- **Better Results**: Google's search algorithm finds more relevant blogs and articles
- **Structured Data**: Returns clean, structured search results
- **No Bot Blocks**: Official API access means no rate limiting or blocking
- **Rich Features**: Access to "People also ask" and related questions
- **Location Targeting**: Better geographic filtering (Canada, English)

## Configuration

### Set SerpAPI Key

```bash
export SERPAPI_API_KEY="your_serpapi_key_here"
# or
export SERPAPI_KEY="your_serpapi_key_here"
```

### Get Your API Key

1. Sign up at https://serpapi.com/
2. Free tier includes 100 searches/month
3. Paid plans available for higher volume

## How It Works

### Search Flow

1. **SerpAPI Google Search** (Primary)
   - Uses Google's search engine via API
   - Searches for: `{query} {city} Ontario` (for Ottawa)
   - Returns up to 20 organic results
   - Filters out social media and spam

2. **DuckDuckGo** (Fallback)
   - Used if SerpAPI key not configured
   - Or if SerpAPI fails/returns no results
   - More limited but still functional

3. **Content Scraping with ScrapingBee**
   - Takes top search results
   - Scrapes with ScrapingBee (handles JavaScript)
   - Falls back to basic HTTP if ScrapingBee unavailable
   - Extracts: title, description, contact, hours, etc.

## Example Use Case: "Sledding Hills in Ottawa"

### Search Process

1. **SerpAPI Query**: `sledding hills Ottawa Ontario`
   
2. **Google Returns**:
   - Blog posts about "Best Sledding Hills in Ottawa"
   - City of Ottawa parks pages
   - Community forums discussing sledding spots
   - News articles about winter activities
   - Review sites with sledding locations

3. **URL Filtering**:
   - Excludes: Social media, Chinese sites, adult content
   - Includes: Blogs, articles, guides, city pages
   - Prioritizes: Results mentioning "Ottawa"

4. **Content Extraction**:
   - Scrapes each relevant URL
   - Extracts: Location names, addresses, descriptions
   - Finds: Hours, contact info, tips/reviews

5. **Result Compilation**:
   - Returns structured data about sledding hills
   - Includes source URLs for verification
   - Provides snippets and descriptions

## Content Discovery Features

### Lenient URL Filtering
Unlike strict business searches, content discovery is more permissive:
- ✅ Blogs and blog posts
- ✅ Review sites (TripAdvisor, Yelp)
- ✅ Community content (Reddit)
- ✅ City/municipal websites
- ✅ News articles
- ✅ Guide websites

### Smart Result Ranking
Results are ranked by:
1. City mentions (Ottawa, etc.)
2. Relevance to query
3. Content type (blogs, guides, official sites)

## API Usage

```python
from ai_orchestrator.server.tools.intelligent_crawler import get_intelligent_crawler

# Initialize with SerpAPI
crawler = get_intelligent_crawler()

# Search and extract content
results = await crawler.intelligent_search_and_extract(
    query="sledding hills",
    city="Ottawa",
    max_results=5,
    focus_areas=['description', 'contact', 'events']
)

# Results include:
# - Title and URL
# - Description/snippet
# - Extracted content from pages
# - Source (serpapi_google, duckduckgo, etc.)
```

## Environment Variables

```bash
# Required for SerpAPI Google Search
SERPAPI_API_KEY=your_key_here

# Required for ScrapingBee (JavaScript rendering)
SCRAPINGBEE_API_KEY=your_key_here
```

## Advantages Over Previous Implementation

### Before (DuckDuckGo Only)
- ❌ Limited search results
- ❌ Poor quality for local content
- ❌ Frequent blocks and failures
- ❌ Irrelevant international results

### After (SerpAPI + ScrapingBee)
- ✅ High-quality Google search results
- ✅ Better local content discovery
- ✅ Official API access (no blocks)
- ✅ Structured, clean data
- ✅ Finds blogs, posts, guides effectively
- ✅ Geographic filtering works better

## Fallback Strategy

1. Try SerpAPI (Google) first
2. If no SerpAPI key: Use DuckDuckGo
3. If DuckDuckGo fails: Return manual search link
4. For scraping:
   - Try ScrapingBee (JavaScript support)
   - Fall back to basic HTTP requests
   - Return search snippet if scraping fails

## Cost Considerations

### SerpAPI
- Free: 100 searches/month
- Paid plans start at $50/month for 5,000 searches
- Only charged for successful searches

### ScrapingBee  
- Free: 1,000 credits
- Paid plans start at $49/month for 100,000 credits
- 1 credit per request

### Optimization
- Limit `max_results` to reduce API calls
- Cache search results when possible
- Use basic HTTP scraping when possible (free)

## Testing

```bash
# Test with SerpAPI
export SERPAPI_API_KEY="your_key"
export SCRAPINGBEE_API_KEY="your_key"

python3 -c "
import asyncio
from ai_orchestrator.server.tools.intelligent_crawler import get_intelligent_crawler

async def test():
    crawler = get_intelligent_crawler()
    results = await crawler.intelligent_search_and_extract(
        query='sledding hills',
        city='Ottawa',
        max_results=3
    )
    print(f'Found {len(results[\"venues\"])} results')
    for venue in results['venues'][:2]:
        print(f'- {venue[\"venue_name\"]}: {venue[\"url\"]}')
    await crawler.close()

asyncio.run(test())
"
```

## Troubleshooting

### No results returned
- Check SERPAPI_API_KEY is set correctly
- Verify API key is active at serpapi.com
- Check API quota hasn't been exceeded

### Poor quality results
- Try more specific queries
- Add location context (city, province)
- Use descriptive search terms

### Scraping failures
- Check SCRAPINGBEE_API_KEY is set
- Verify ScrapingBee quota available
- Some sites may block all scraping

## Summary

SerpAPI integration transforms web search from unreliable to professional-grade, enabling discovery of blogs, posts, and local content with Google's search quality and none of the bot-blocking issues.
