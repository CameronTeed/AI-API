# 🎯 AI Date Ideas Manager - Web UI & Scraping Guide

A comprehensive web interface and automated scraping system for managing date ideas in your AI orchestrator. This system allows you to easily add, search, and discover romantic date ideas with AI-powered semantic search.

## 🌟 Features

### 📝 Web UI Features
- **Visual Management**: Add, edit, view, and delete date ideas through a beautiful web interface
- **Semantic Search**: AI-powered search using vector embeddings for finding perfect date matches
- **Real-time Statistics**: View your collection size, vector coverage, and database health
- **Mobile Responsive**: Works perfectly on desktop, tablet, and mobile devices

### 🌐 Web Scraping Features
- **Multi-Source Scraping**: Automatically discover date ideas from:
  - **Yelp**: Restaurants, bars, entertainment venues
  - **Eventbrite**: Date events, workshops, couple experiences
  - **TripAdvisor**: Attractions, activities, tourist spots
- **Intelligent Deduplication**: Automatically removes duplicate entries
- **Ethical Scraping**: Respectful delays and rate limiting
- **Automatic Processing**: Generates vector embeddings for all scraped content

### 📊 Import/Export Features
- **JSON Export**: Backup your entire date ideas collection
- **JSON Import**: Restore from backups or import from other sources
- **Bulk Operations**: Process multiple ideas at once
- **Format Validation**: Ensures data integrity during import

### 🔧 API Features
- **RESTful API**: Full CRUD operations via HTTP endpoints
- **Search API**: Programmatic access to vector search
- **Health Monitoring**: Database and vector store status endpoints

## 🚀 Quick Start

### 1. Install and Run
```bash
# Navigate to the ai_orchestrator directory
cd /home/cameron/ai-api/ai_orchestrator

# Run the quick setup script
python3 run_web_ui.py
```

This script will:
- Install all required dependencies
- Test database connectivity
- Start the web UI at http://localhost:8000

### 2. Access the Web Interface

Open your browser and go to **http://localhost:8000**

#### Main Navigation:
- 🏠 **Home**: View all your date ideas with filters and sorting
- ➕ **Add New**: Manual form to add custom date ideas
- 🔍 **Search**: AI-powered semantic search interface
- 🌐 **Web Scrape**: Automated discovery from multiple websites
- 🔄 **Import/Export**: Backup and restore functionality

## 📱 Using the Web UI

### Adding Date Ideas Manually

1. Click **"Add New"** in the navigation
2. Fill out the form with details:
   - **Title**: Name of the date idea
   - **Description**: What makes it special
   - **Categories**: Tags (comma-separated)
   - **Location**: City, coordinates
   - **Details**: Price tier, duration, rating
   - **Options**: Indoor/outdoor, kid-friendly
3. Click **"Save Date Idea"**
4. Vector embeddings are automatically generated!

### Searching for Perfect Dates

1. Click **"Search"** in the navigation
2. Enter natural language queries like:
   - "romantic dinner for anniversary"
   - "outdoor adventure for active couple"
   - "budget-friendly fun activities"
   - "rainy day indoor dates"
3. Adjust the number of results (5-50)
4. View results with similarity scores and source information

### Web Scraping for Discovery

1. Click **"Web Scrape"** in the navigation
2. Configure your scraping:
   - **City**: Target location (Ottawa, Toronto, etc.)
   - **Max Results**: How many ideas per source (5-30)
   - **Auto-Save**: Whether to save directly to database
3. Click **"Start Web Scraping"**
4. Wait for results (typically 2-5 minutes)
5. Review the preview and check your home page for new ideas

### Importing and Exporting

#### To Export Your Data:
1. Go to **Import/Export** page
2. Click **"Export All Date Ideas"**
3. Download the generated JSON file for backup

#### To Import Data:
1. Place your JSON file in the ai_orchestrator directory
2. Go to **Import/Export** page  
3. Enter the filename (e.g., `scraped_ideas_20250913_143022.json`)
4. Click **"Import Date Ideas"**

## 🔧 Advanced Usage

### Using the REST API

The web UI also provides a full REST API:

```bash
# Get all date ideas
curl http://localhost:8000/api/date-ideas

# Search for date ideas
curl "http://localhost:8000/api/search?query=romantic%20dinner&top_k=5"

# Add a new date idea
curl -X POST http://localhost:8000/api/date-ideas \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Rooftop Bar Experience",
    "description": "Trendy rooftop bar with city views",
    "city": "Ottawa",
    "price_tier": 3,
    "categories": ["bar", "views", "trendy"]
  }'

# Health check
curl http://localhost:8000/health
```

### Command-Line Scraping

You can also run scraping from the command line:

```bash
# Scrape and save to database
python3 web_scraper.py --city Ottawa --max-per-source 15 --save-db

# Scrape and export to JSON only
python3 web_scraper.py --city Toronto --max-per-source 10 --export-json

# Custom output file
python3 web_scraper.py --city Montreal --output my_montreal_ideas.json --save-db
```

### Direct Vector Store Testing

Test your vector store directly:

```bash
# Test existing vectors in database
python3 search_vector_store.py

# Add new data and test
python3 populate_vector_store.py
```

## 🔧 Configuration

### Environment Variables

Create or update your `.env` file:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dateideasdb
DB_USER=your_user
DB_PASSWORD=your_password

# Web UI Configuration  
WEB_UI_PORT=8000
WEB_UI_HOST=0.0.0.0

# OpenAI (for your main AI features)
OPENAI_API_KEY=your_openai_key

# Optional: Search API keys for enhanced scraping
SERPAPI_KEY=your_serpapi_key
```

### Database Setup

If you haven't set up PostgreSQL yet:

```bash
# Initialize the database
python3 init_database.py

# Test the connection
python3 -c "from server.db_config import test_connection; print('✅ Connected' if test_connection() else '❌ Failed')"
```

## 📊 Data Format

### JSON Import/Export Format

```json
[
  {
    "title": "Romantic Dinner at Waterfront",
    "description": "Beautiful restaurant with stunning water views and intimate ambiance. Perfect for anniversaries and special occasions.",
    "city": "Ottawa",
    "categories": ["romantic", "dinner", "waterfront"],
    "price_tier": 3,
    "duration_min": 120,
    "indoor": true,
    "kid_friendly": false,
    "website": "https://restaurant-example.com",
    "phone": "(613) 555-0123",
    "rating": 4.5,
    "review_count": 150,
    "lat": 45.4215,
    "lon": -75.6972
  }
]
```

### Database Schema

The system automatically manages:
- **Events**: Core date idea information
- **Categories**: Tagging system with many-to-many relationships
- **Locations**: Geographic data for mapping
- **Vector Embeddings**: 384-dimensional semantic vectors for search

## 🛠️ Troubleshooting

### Common Issues

#### "No module named 'fastapi'"
```bash
pip install -r requirements.txt
```

#### "Database connection failed"
1. Ensure PostgreSQL is running
2. Check your `.env` file configuration
3. Run `python3 init_database.py`

#### "Vector store model not available"
```bash
pip install sentence-transformers
```

#### Scraping returns no results
1. Check your internet connection
2. Try different cities or search terms
3. Some sites may have changed their structure

#### Import fails with "File not found"
1. Ensure the JSON file is in the `ai_orchestrator` directory
2. Check the exact filename (case-sensitive)
3. Verify the file is valid JSON

### Performance Tips

1. **For large collections**: Increase vector search cache
2. **For slow scraping**: Reduce `max_per_source` parameter
3. **For memory issues**: Restart the web UI periodically
4. **For search accuracy**: Use more descriptive search terms

## 🎯 Next Steps

Once you have the web UI running:

1. **Start with manual entries**: Add 5-10 date ideas manually to test
2. **Try semantic search**: Search for different types of dates
3. **Run a small scrape**: Test with 5 results per source
4. **Export and backup**: Create a backup of your data
5. **Integrate with your main AI**: Use the API endpoints in your chat system

## 🔗 Integration with Main AI System

Your main AI chat system can now use:

```python
# In your chat handler
import requests

# Search for date ideas
response = requests.get(
    "http://localhost:8000/api/search",
    params={"query": user_preference, "top_k": 5}
)
date_suggestions = response.json()["results"]

# Add new ideas from user feedback
new_idea = {
    "title": "User's Custom Idea",
    "description": extracted_from_chat,
    "city": user_location
}
requests.post("http://localhost:8000/api/date-ideas", json=new_idea)
```

## 🎉 Enjoy!

You now have a powerful, AI-enhanced date idea management system! The combination of manual curation, automated web scraping, and semantic search gives you the best of all worlds for helping users find perfect dates.

Happy dating! 💕