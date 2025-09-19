#!/usr/bin/env python3
"""
Web UI for managing date ideas in the AI Orchestrator system.
Provides a user-friendly interface for adding, editing, viewing, and searching date ideas.
"""
import os
import sys
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

# FastAPI and web dependencies
from fastapi import FastAPI, HTTPException, Form, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import json

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not available.")

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from server.tools.vector_store import get_vector_store
from server.db_config import get_db_config, test_connection
from web_scraper import DateIdeaScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="AI Date Ideas Manager",
    description="Web interface for managing date ideas in the AI Orchestrator system",
    version="1.0.0"
)

# Templates and static files
templates = Jinja2Templates(directory="templates")

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models
class DateIdeaCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=1000)
    categories: List[str] = Field(default_factory=list)
    city: str = Field("", max_length=100)
    lat: float = Field(0.0)
    lon: float = Field(0.0)
    price_tier: int = Field(1, ge=1, le=5)
    duration_min: int = Field(60, ge=15, le=1440)
    indoor: bool = Field(False)
    kid_friendly: bool = Field(False)
    website: str = Field("", max_length=500)
    phone: str = Field("", max_length=20)
    rating: float = Field(0.0, ge=0.0, le=5.0)
    review_count: int = Field(0, ge=0)

class DateIdeaUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    categories: Optional[List[str]] = None
    city: Optional[str] = Field(None, max_length=100)
    lat: Optional[float] = None
    lon: Optional[float] = None
    price_tier: Optional[int] = Field(None, ge=1, le=5)
    duration_min: Optional[int] = Field(None, ge=15, le=1440)
    indoor: Optional[bool] = None
    kid_friendly: Optional[bool] = None
    website: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    review_count: Optional[int] = Field(None, ge=0)

# Global vector store instance
vector_store = None

def get_vector_store_instance():
    """Get the vector store instance (singleton pattern)"""
    global vector_store
    if vector_store is None:
        vector_store = get_vector_store()
    return vector_store

def get_db_connection():
    """Get database connection"""
    try:
        config = get_db_config()
        return config.get_connection()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# Routes

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page showing all date ideas"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT event_id, title, description, city, price_tier, rating, 
                       indoor, kid_friendly, duration_min,
                       CASE WHEN embedding IS NOT NULL THEN true ELSE false END as has_vector
                FROM event 
                ORDER BY event_id DESC
            """)
            date_ideas = cur.fetchall()
            
            # Convert to list of dicts
            ideas = []
            for row in date_ideas:
                ideas.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2][:100] + '...' if len(row[2] or '') > 100 else row[2],
                    'city': row[3],
                    'price_tier': row[4],
                    'rating': row[5],
                    'indoor': row[6],
                    'kid_friendly': row[7],
                    'duration_min': row[8],
                    'has_vector': row[9]
                })
        
        conn.close()
        return templates.TemplateResponse("home.html", {"request": request, "date_ideas": ideas})
    
    except Exception as e:
        logger.error(f"Error loading home page: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/add", response_class=HTMLResponse)
async def add_form(request: Request):
    """Show add new date idea form"""
    return templates.TemplateResponse("add.html", {"request": request})

@app.post("/add")
async def add_date_idea(
    title: str = Form(...),
    description: str = Form(""),
    categories: str = Form(""),
    city: str = Form(""),
    lat: float = Form(0.0),
    lon: float = Form(0.0),
    price_tier: int = Form(1),
    duration_min: int = Form(60),
    indoor: bool = Form(False),
    kid_friendly: bool = Form(False),
    website: str = Form(""),
    phone: str = Form(""),
    rating: float = Form(0.0),
    review_count: int = Form(0)
):
    """Add a new date idea"""
    try:
        # Parse categories
        category_list = [cat.strip() for cat in categories.split(',') if cat.strip()] if categories else []
        
        # Create date idea object
        date_idea = {
            'title': title,
            'description': description,
            'categories': category_list,
            'city': city,
            'lat': lat,
            'lon': lon,
            'price_tier': price_tier,
            'duration_min': duration_min,
            'indoor': indoor,
            'kid_friendly': kid_friendly,
            'website': website,
            'phone': phone,
            'rating': rating,
            'review_count': review_count
        }
        
        # Add to vector store (this will also save to database)
        vs = get_vector_store_instance()
        success = vs.add_date_ideas([date_idea])
        
        if success:
            return RedirectResponse(url="/", status_code=302)
        else:
            raise HTTPException(status_code=500, detail="Failed to add date idea")
    
    except Exception as e:
        logger.error(f"Error adding date idea: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/edit/{idea_id}", response_class=HTMLResponse)
async def edit_form(request: Request, idea_id: int):
    """Show edit form for a date idea"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT event_id, title, description, city, lat, lon, price_tier, 
                       duration_min, indoor, kid_friendly, website, phone, rating, review_count
                FROM event 
                WHERE event_id = %s
            """, (idea_id,))
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Date idea not found")
            
            # Get categories
            cur.execute("""
                SELECT c.name 
                FROM category c 
                JOIN event_category ec ON c.category_id = ec.category_id 
                WHERE ec.event_id = %s
            """, (idea_id,))
            categories = [row[0] for row in cur.fetchall()]
            
            idea = {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'city': row[3],
                'lat': row[4],
                'lon': row[5],
                'price_tier': row[6],
                'duration_min': row[7],
                'indoor': row[8],
                'kid_friendly': row[9],
                'website': row[10],
                'phone': row[11],
                'rating': row[12],
                'review_count': row[13],
                'categories': ', '.join(categories)
            }
        
        conn.close()
        return templates.TemplateResponse("edit.html", {"request": request, "idea": idea})
    
    except Exception as e:
        logger.error(f"Error loading edit form: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/edit/{idea_id}")
async def update_date_idea(
    idea_id: int,
    title: str = Form(...),
    description: str = Form(""),
    categories: str = Form(""),
    city: str = Form(""),
    lat: float = Form(0.0),
    lon: float = Form(0.0),
    price_tier: int = Form(1),
    duration_min: int = Form(60),
    indoor: bool = Form(False),
    kid_friendly: bool = Form(False),
    website: str = Form(""),
    phone: str = Form(""),
    rating: float = Form(0.0),
    review_count: int = Form(0)
):
    """Update a date idea"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Update basic event info
            cur.execute("""
                UPDATE event 
                SET title = %s, description = %s, city = %s, lat = %s, lon = %s,
                    price_tier = %s, duration_min = %s, indoor = %s, kid_friendly = %s,
                    website = %s, phone = %s, rating = %s, review_count = %s
                WHERE event_id = %s
            """, (title, description, city, lat, lon, price_tier, duration_min, 
                  indoor, kid_friendly, website, phone, rating, review_count, idea_id))
            
            # Update categories
            category_list = [cat.strip() for cat in categories.split(',') if cat.strip()] if categories else []
            
            # Remove existing categories
            cur.execute("DELETE FROM event_category WHERE event_id = %s", (idea_id,))
            
            # Add new categories
            for category_name in category_list:
                # Insert category if doesn't exist
                cur.execute("INSERT INTO category (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (category_name,))
                
                # Get category ID
                cur.execute("SELECT category_id FROM category WHERE name = %s", (category_name,))
                category_id = cur.fetchone()[0]
                
                # Link to event
                cur.execute("INSERT INTO event_category (event_id, category_id) VALUES (%s, %s)", (idea_id, category_id))
            
            # Regenerate embedding for updated event
            vs = get_vector_store_instance()
            if hasattr(vs, 'regenerate_embedding'):
                vs.regenerate_embedding(idea_id)
        
        conn.commit()
        conn.close()
        return RedirectResponse(url="/", status_code=302)
    
    except Exception as e:
        logger.error(f"Error updating date idea: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete/{idea_id}")
async def delete_date_idea(idea_id: int):
    """Delete a date idea"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Delete from event_category first (foreign key constraint)
            cur.execute("DELETE FROM event_category WHERE event_id = %s", (idea_id,))
            
            # Delete from event
            cur.execute("DELETE FROM event WHERE event_id = %s", (idea_id,))
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Date idea not found")
        
        conn.commit()
        conn.close()
        return RedirectResponse(url="/", status_code=302)
    
    except Exception as e:
        logger.error(f"Error deleting date idea: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", response_class=HTMLResponse)
async def search_form(request: Request):
    """Show search form"""
    return templates.TemplateResponse("search.html", {"request": request, "results": None})

@app.post("/search", response_class=HTMLResponse)
async def search_date_ideas(request: Request, query: str = Form(...), top_k: int = Form(10)):
    """Search date ideas using vector similarity"""
    try:
        vs = get_vector_store_instance()
        results = vs.search(query, top_k=top_k)
        
        return templates.TemplateResponse("search.html", {
            "request": request, 
            "results": results, 
            "query": query,
            "count": len(results)
        })
    
    except Exception as e:
        logger.error(f"Error searching date ideas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get vector store statistics"""
    try:
        vs = get_vector_store_instance()
        stats = vs.get_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API endpoints for external integration
@app.post("/api/date-ideas")
async def api_create_date_idea(date_idea: DateIdeaCreate):
    """API endpoint to create a new date idea"""
    try:
        vs = get_vector_store_instance()
        success = vs.add_date_ideas([date_idea.dict()])
        
        if success:
            return {"message": "Date idea created successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to create date idea")
    
    except Exception as e:
        logger.error(f"API error creating date idea: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/date-ideas")
async def api_list_date_ideas(limit: int = 50, offset: int = 0):
    """API endpoint to list date ideas"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT event_id, title, description, city, lat, lon, price_tier, 
                       duration_min, indoor, kid_friendly, website, phone, rating, review_count
                FROM event 
                ORDER BY event_id DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
            rows = cur.fetchall()
            
            ideas = []
            for row in rows:
                ideas.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'city': row[3],
                    'lat': row[4],
                    'lon': row[5],
                    'price_tier': row[6],
                    'duration_min': row[7],
                    'indoor': row[8],
                    'kid_friendly': row[9],
                    'website': row[10],
                    'phone': row[11],
                    'rating': row[12],
                    'review_count': row[13]
                })
        
        conn.close()
        return {"date_ideas": ideas, "count": len(ideas)}
    
    except Exception as e:
        logger.error(f"API error listing date ideas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def api_search_date_ideas(query: str, top_k: int = 10):
    """API endpoint to search date ideas"""
    try:
        vs = get_vector_store_instance()
        results = vs.search(query, top_k=top_k)
        return {"results": results, "query": query, "count": len(results)}
    
    except Exception as e:
        logger.error(f"API error searching date ideas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Web scraping routes
@app.get("/scrape", response_class=HTMLResponse)
async def scrape_form(request: Request):
    """Show web scraping form"""
    return templates.TemplateResponse("scrape.html", {"request": request})

@app.post("/scrape")
async def start_scraping(
    city: str = Form("Ottawa"),
    max_per_source: int = Form(10),
    save_to_db: bool = Form(False)
):
    """Start web scraping process"""
    try:
        logger.info(f"Starting scraping for city: {city}")
        
        # Initialize scraper
        scraper = DateIdeaScraper()
        
        # Scrape from all sources
        all_ideas = scraper.scrape_all(city, max_per_source)
        
        if not all_ideas:
            raise HTTPException(status_code=404, detail="No date ideas found during scraping")
        
        # Deduplicate
        unique_ideas = scraper.deduplicate_ideas(all_ideas)
        
        # Save to database if requested
        saved_count = 0
        if save_to_db:
            success = scraper.save_to_database(unique_ideas)
            if success:
                saved_count = len(unique_ideas)
        
        # Export to JSON for preview
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"scraped_ideas_{timestamp}.json"
        scraper.export_to_json(unique_ideas, json_filename)
        
        return JSONResponse(content={
            "success": True,
            "total_scraped": len(all_ideas),
            "unique_ideas": len(unique_ideas),
            "saved_to_db": saved_count,
            "json_file": json_filename,
            "preview": [
                {
                    "title": idea.title,
                    "description": idea.description[:100] + "..." if len(idea.description) > 100 else idea.description,
                    "source": idea.source,
                    "city": idea.city,
                    "rating": idea.rating
                }
                for idea in unique_ideas[:5]
            ]
        })
    
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scraping-status")
async def get_scraping_status():
    """Get current scraping status"""
    # This could be enhanced with actual background task tracking
    return {"status": "ready", "message": "Ready to start scraping"}

# Bulk import/export routes
@app.get("/import-export", response_class=HTMLResponse)
async def import_export_form(request: Request):
    """Show import/export form"""
    return templates.TemplateResponse("import_export.html", {"request": request})

@app.post("/import-json")
async def import_json_file(file: str = Form(...)):
    """Import date ideas from JSON file"""
    try:
        # Load JSON file
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate format
        if not isinstance(data, list):
            raise HTTPException(status_code=400, detail="JSON file must contain an array of date ideas")
        
        # Add to vector store
        vs = get_vector_store_instance()
        success = vs.add_date_ideas(data)
        
        if success:
            return {"message": f"Successfully imported {len(data)} date ideas", "count": len(data)}
        else:
            raise HTTPException(status_code=500, detail="Failed to import date ideas")
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="JSON file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file format")
    except Exception as e:
        logger.error(f"Error importing JSON: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export-json")
async def export_json():
    """Export all date ideas to JSON"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT event_id, title, description, city, lat, lon, price_tier, 
                       duration_min, indoor, kid_friendly, website, phone, rating, review_count
                FROM event 
                ORDER BY event_id
            """)
            rows = cur.fetchall()
            
            # Get categories for each event
            ideas = []
            for row in rows:
                event_id = row[0]
                cur.execute("""
                    SELECT c.name 
                    FROM category c 
                    JOIN event_category ec ON c.category_id = ec.category_id 
                    WHERE ec.event_id = %s
                """, (event_id,))
                categories = [cat[0] for cat in cur.fetchall()]
                
                idea = {
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'city': row[3],
                    'lat': row[4],
                    'lon': row[5],
                    'price_tier': row[6],
                    'duration_min': row[7],
                    'indoor': row[8],
                    'kid_friendly': row[9],
                    'website': row[10],
                    'phone': row[11],
                    'rating': row[12],
                    'review_count': row[13],
                    'categories': categories,
                    'exported_at': datetime.now().isoformat()
                }
                ideas.append(idea)
        
        conn.close()
        
        # Create export filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"date_ideas_export_{timestamp}.json"
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(ideas, f, indent=2, ensure_ascii=False)
        
        return {"message": f"Exported {len(ideas)} date ideas to {filename}", "filename": filename, "count": len(ideas)}
    
    except Exception as e:
        logger.error(f"Error exporting JSON: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db_status = test_connection()
        vs = get_vector_store_instance()
        vs_status = hasattr(vs, 'model') and vs.model is not None
        
        return {
            "status": "healthy" if db_status and vs_status else "unhealthy",
            "database": "connected" if db_status else "disconnected",
            "vector_store": "loaded" if vs_status else "not_loaded",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def main():
    """Main function to run the web UI"""
    logger.info("🚀 Starting AI Date Ideas Manager Web UI")
    
    # Test database connection
    if not test_connection():
        logger.error("❌ Database connection failed! Please check your PostgreSQL setup.")
        sys.exit(1)
    
    logger.info("✅ Database connection successful")
    
    # Test vector store
    try:
        vs = get_vector_store_instance()
        if not hasattr(vs, 'model') or vs.model is None:
            logger.error("❌ Vector store model not available. Please install sentence-transformers.")
            sys.exit(1)
        logger.info("✅ Vector store loaded successfully")
    except Exception as e:
        logger.error(f"❌ Vector store initialization failed: {e}")
        sys.exit(1)
    
    # Get port from environment or use default
    port = int(os.getenv('WEB_UI_PORT', '8000'))
    host = os.getenv('WEB_UI_HOST', '0.0.0.0')
    
    logger.info(f"🌐 Starting web server on http://{host}:{port}")
    logger.info("📝 Available endpoints:")
    logger.info("  - http://localhost:8000/          (Home page)")
    logger.info("  - http://localhost:8000/add       (Add new date idea)")
    logger.info("  - http://localhost:8000/search    (Search date ideas)")
    logger.info("  - http://localhost:8000/api/...   (API endpoints)")
    logger.info("  - http://localhost:8000/health    (Health check)")
    
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()