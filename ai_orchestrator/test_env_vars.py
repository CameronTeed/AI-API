#!/usr/bin/env python3
"""
Test if environment variables are loaded correctly
"""

import os
from dotenv import load_dotenv

print("=== Environment Variable Test ===")

# Try loading from .env explicitly
print("Loading .env file...")
load_dotenv()

# Check all relevant env vars
print(f"SERPAPI_KEY: {os.getenv('SERPAPI_KEY')}")
print(f"SERPAPI_API_KEY: {os.getenv('SERPAPI_API_KEY')}")
print(f"SCRAPINGBEE_API_KEY: {os.getenv('SCRAPINGBEE_API_KEY')[:10] if os.getenv('SCRAPINGBEE_API_KEY') else None}...")

# Test the intelligent crawler constructor
print("\n=== Testing Intelligent Crawler ===")
from server.tools.intelligent_crawler import get_intelligent_crawler

crawler = get_intelligent_crawler()
print(f"Crawler SerpAPI key: {'SET' if crawler.serpapi_key else 'NOT SET'}")
print(f"Crawler ScrapingBee key: {'SET' if crawler.scrapingbee_api_key else 'NOT SET'}")

if crawler.serpapi_key:
    print(f"SerpAPI key preview: {crawler.serpapi_key[:10]}...")