# Web Scraping Improvements

## Summary of Enhancements

The web scraping functionality has been significantly improved with the following enhancements:

### 1. **Improved HTTP Client Configuration**
- Added proper timeout handling (30s total, 10s connect)
- Enhanced HTTP headers to better mimic real browsers
- Added connection pooling limits to prevent resource exhaustion
- Implemented rate limiting to avoid overwhelming target servers

### 2. **Robust Error Handling & Retry Logic**
- Automatic retry with exponential backoff (up to 3 attempts)
- Smart detection of bot-blocking responses (captcha, cloudflare, etc.)
- Graceful fallback to ScrapingBee API when encountering 403/429 errors
- Better handling of timeout exceptions
- Early termination after multiple scraping failures to prevent delays

### 3. **Intelligent Search Result Filtering**
- **Relevance Filtering**: Excludes irrelevant domains (social media, Q&A sites, non-English sites)
- **Geographic Validation**: Ensures results actually match the requested city
- **Content Validation**: Filters out forums, questions, dating sites, etc.
- **Domain Scoring**: Prefers business websites with restaurant-related keywords
- **Expanded Search**: Fetches 20 results and filters to find 10 relevant ones
- **Location Enhancement**: Adds "Ontario Canada" for Ottawa searches to improve targeting

### 4. **Enhanced Content Extraction**

#### Venue Name Extraction
- Prioritizes Open Graph site name (most accurate)
- Checks structured JSON-LD data
- Falls back through multiple CSS selectors
- Cleans up title suffixes (e.g., "Restaurant | City")

#### Description Extraction
- Multi-level fallback strategy:
  1. Meta description tag
  2. Open Graph description
  3. JSON-LD structured data (handles both objects and arrays)
  4. Common CSS selectors
  5. First substantial paragraph
- Filters out navigation, footer, and cookie notices
- Validates description length and quality

#### Contact Information
- Extracts from structured data (JSON-LD) first
- Tries specific CSS selectors before regex patterns
- Validates phone numbers (minimum 10 digits)
- Validates email addresses (proper format)
- Better address pattern matching with postal code support

#### Operating Hours
- Parses JSON-LD openingHours and openingHoursSpecification
- Handles both single and array formats
- Validates content contains time/day indicators
- Supports multiple hours container elements
- Extracts up to 7 days of hours

### 5. **Improved Web Search**
- Added DuckDuckGo search with error handling
- Geographic targeting with "Ontario Canada" suffix for better local results
- Regional preference (Canadian English)
- City-based filtering of results
- Graceful degradation when search is unavailable
- Fallback to simpler queries if detailed search fails

### 6. **ScrapingBee Integration Improvements**
- Reduced timeout to 45 seconds (from 90) to prevent long delays
- Increased wait time for JavaScript rendering (3s)
- Network idle detection for better content loading
- Resource blocking for faster page loads
- Ad blocking enabled
- Better error handling for 500/503 errors
- Automatic fallback to simpler parameters on validation errors
- Skip scraping after 3 consecutive failures

### 7. **Resource Management**
- Proper cleanup with async close methods
- Connection reuse through keep-alive
- Rate limiting per domain to be respectful
- Early termination on repeated failures

## Key Features

✅ **Retry Logic**: Automatically retries failed requests with exponential backoff
✅ **Bot Detection**: Detects and handles anti-bot measures
✅ **Fallback Strategy**: ScrapingBee API used when standard scraping fails
✅ **Multi-Source Extraction**: Tries multiple methods to extract each piece of information
✅ **Validation**: Validates extracted data for quality and relevance
✅ **Rate Limiting**: Respects target servers with proper delays
✅ **Error Recovery**: Graceful degradation when features are unavailable
✅ **Smart Filtering**: Excludes irrelevant search results (wrong country, wrong type)
✅ **Geographic Targeting**: Ensures results match the requested city
✅ **Fast Failure**: Stops trying after multiple errors to avoid delays

## Usage Example

```python
from ai_orchestrator.server.tools.intelligent_crawler import get_intelligent_crawler

# Get crawler instance
crawler = get_intelligent_crawler()

# Extract venue information
result = await crawler.extract_venue_information(
    url="https://example-restaurant.com",
    venue_name="Example Restaurant",
    focus_areas=['description', 'contact', 'hours', 'pricing']
)

# Intelligent search with automatic extraction
search_result = await crawler.intelligent_search_and_extract(
    query="pasta restaurants",
    city="Ottawa",
    max_results=5,
    focus_areas=['description', 'contact', 'hours', 'pricing', 'events']
)

# Clean up
await crawler.close()
```

## Configuration

Set the `SCRAPINGBEE_API_KEY` environment variable to enable advanced scraping for JavaScript-heavy sites:

```bash
export SCRAPINGBEE_API_KEY="your_api_key_here"
```

## What Was Fixed

1. **Timeout Issues**: Added proper timeout configuration and handling (45s max)
2. **Bot Detection**: Better handling of sites that block scrapers
3. **Poor Extraction**: Multi-level fallback ensures better data extraction
4. **Resource Leaks**: Proper cleanup and connection management
5. **Search Failures**: Robust error handling in web search
6. **Rate Limiting**: Added delays to avoid overwhelming servers
7. **Data Validation**: Better validation of extracted information
8. **Irrelevant Results**: Smart filtering of search results by location and relevance
9. **Wrong Geographic Results**: Validates city matches in title/snippet/URL
10. **Long Delays**: Early termination after repeated failures
11. **Non-English Sites**: Filters out Chinese, Russian, Portuguese sites
12. **Spam Sites**: Excludes dating, adult, Q&A, and forum sites

## Testing

Run the test script to verify improvements:

```bash
python3 test_scraping.py
```

This will test:
- Basic venue information extraction
- Contact information extraction
- Intelligent search with automatic crawling
- Error handling and fallbacks
- Geographic filtering
- Relevance filtering
