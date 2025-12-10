# Cleanup Analysis - What's Actually Needed

## 🎯 Current System Architecture

The system uses these ACTUAL tools (defined in `tools_config.py`):

### ✅ ACTIVELY USED TOOLS
1. **search_date_ideas** - Vector store search
2. **search_featured_dates** - Featured dates search
3. **google_places_search** - Google Places API
4. **find_nearby_venues** - Nearby venues search
5. **get_directions** - Google Maps directions
6. **web_scrape_venue_info** - Website scraping
7. **enhanced_web_search** - Web search
8. **geocode_location** - Address to coordinates
9. **web_search** - Legacy web search
10. **scrapingbee_scrape** - Advanced scraping
11. **eventbrite_search** - Event search

All these tools are implemented in `agent_tools.py` and called via the LLM engine.

## ❌ UNUSED/JUNK FILES TO DELETE

### Final Folder (NOT INTEGRATED)
- `final/` - Entire folder
  - app.py - Standalone Streamlit app
  - evaluation.py - Evaluation script
  - fetch_real_data.py - Data fetching
  - ga_planner.py - Genetic algorithm
  - heuristic_planner.py - Heuristic planner
  - nlp_classifier.py - NLP classifier
  - ottawa_venues.csv - Venue data
  - planner_utils.py - Utilities
  - requirements.txt - Dependencies
  - spacy_parser.py - SpaCy parser
  - ui_components.py - UI components

**Reason**: Not imported or used anywhere. Created but never integrated.

### Date Planner Tools (NOT INTEGRATED)
- `server/tools/date_planner_service.py` - Service layer
- `server/tools/date_planner_tool.py` - Tool wrapper
- `server/tools/date_planner_utils.py` - Utilities
- `server/tools/venue_database.py` - Database layer
- `migrate_venues_to_db.py` - Migration script

**Reason**: Created but never called from chat handler or LLM engine.

### Integration Documentation (OUTDATED)
- `INTEGRATION_GUIDE.md`
- `FINAL_INTEGRATION_SUMMARY.md`
- `QUICK_START_DATE_PLANNER.md`
- `INTEGRATION_COMPLETE.md`
- `INTEGRATION_CHECKLIST.md`
- `README_INTEGRATION.md`
- `FINAL_SUMMARY.md`

**Reason**: Documents for integration that never happened.

### Other Unused Files
- `docs/INTEGRATION_GUIDE.md` - Duplicate
- `inspect_vector_store.py` - Inspection utility
- `chat_service_pb2.py` - Generated protobuf
- `chat_service_pb2_grpc.py` - Generated protobuf

## ✅ KEEP THESE FILES

### Core System
- `server/chat_handler.py` - Main chat handler
- `server/llm/engine.py` - LLM engine
- `server/llm/tools_config.py` - Tool definitions
- `server/tools/agent_tools.py` - All tool implementations
- `server/tools/vector_store.py` - Vector search
- `server/tools/web_search.py` - Web search
- `server/tools/db_client.py` - Database client
- `server/tools/chat_context_storage.py` - Chat memory
- `server/tools/tool_executor.py` - Tool execution

### Configuration
- `requirements.txt` - Dependencies
- `pyproject.toml` - Project config
- `setup.py` - Setup script
- `Makefile` - Build commands

### Database
- `sql/schema.sql` - Database schema
- `flyway/` - Database migrations

### API & Web
- `server/api/` - REST API
- `templates/` - HTML templates
- `static/` - Static files
- `web_ui.py` - Web UI

### Tests
- `tests/` - Test files

## 📊 Summary

**Files to Delete**: ~30 files
**Files to Keep**: ~50 files
**Space Saved**: ~5-10 MB

## 🚀 Next Steps

1. Delete final/ folder
2. Delete date_planner tools
3. Delete integration documentation
4. Delete unused utilities
5. Verify system still works

