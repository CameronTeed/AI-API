# AI Date Ideas Orchestrator

An intelligent AI-powered chat system that helps users find date ideas in their city using semantic search, real-time data, and agent tools.

## Features

- **🤖 Intelligent Chat Interface**: Natural language conversation for finding date ideas
- **🔍 Semantic Search**: Vector-based search across curated date ideas
- **🌐 Real-Time Data**: Integration with Google Places, Maps, and web search
- **🎯 Multi-Tool Agent**: Automatically uses 3-4+ tools per request for comprehensive results
- **💾 Persistent Storage**: Chat history and context saved to PostgreSQL
- **🖥️ Admin Portal**: Web UI for managing date ideas and viewing analytics

### Agent Tools (11 Total)

The system uses multiple tools automatically for every request:

**Database Tools:**
- `search_date_ideas` - Semantic search of curated ideas
- `search_featured_dates` - Find special/unique experiences

**Real-Time Data:**
- `google_places_search` - Current venue discovery
- `find_nearby_venues` - Location-based recommendations
- `get_directions` - Travel planning

**Web Research:**
- `enhanced_web_search` - Events, reviews, deals
- `eventbrite_search` - Event platform search
- `web_scrape_venue_info` - Venue detail extraction
- `scrapingbee_scrape` - Advanced scraping

**Utilities:**
- `geocode_location` - Address conversion
- `web_search` - General web search

## System Components

### 1. Chat Server (gRPC)
The main server that handles chat requests using OpenAI's GPT models with function calling.

**Features:**
- Vector database search for curated date ideas
- Google Places API for real-time venue discovery
- Google Maps API for directions and travel time
- Web scraping for detailed venue information
- Context-aware chat with persistent history

### 2. Admin Web UI
A FastAPI-based web portal for managing date ideas.

**Features:**
- Add new date ideas to the vector database
- Edit and delete existing ideas
- Search and filter the database
- View statistics and analytics
- Bulk import/export

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ with pgvector extension
- OpenAI API key
- (Optional) Google Places/Maps API keys

### Installation

1. **Clone and install dependencies:**
```bash
cd ai_orchestrator
make install
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. **Setup database and vector store:**
```bash
make setup
```

4. **Start the chat server:**
```bash
make start-server
```

5. **Start the admin web UI (in another terminal):**
```bash
make web-ui
```

## Environment Variables

### Required

- `OPENAI_API_KEY` - OpenAI API key for GPT models
- `DB_HOST` - PostgreSQL host (default: localhost)
- `DB_PORT` - PostgreSQL port (default: 5432)
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password
- `DB_NAME` - Database name

### Optional

- `GOOGLE_PLACES_API_KEY` - For real-time venue search
- `GOOGLE_MAPS_API_KEY` - For directions and maps
- `SEARCH_API_KEY` - For web search (SerpAPI or similar)
- `SEARCH_PROVIDER` - Search provider (default: serpapi)
- `DEFAULT_CITY` - Default city for searches (default: Ottawa)
- `PORT` - gRPC server port (default: 7000)

## Usage

### Chat Server

The chat server uses gRPC. Connect with any gRPC client or use the provided examples.

**Example request:**
```python
import grpc
import chat_service_pb2
import chat_service_pb2_grpc

channel = grpc.insecure_channel('localhost:7000')
stub = chat_service_pb2_grpc.AiOrchestratorStub(channel)

request = chat_service_pb2.ChatRequest(
    messages=[
        chat_service_pb2.ChatMessage(
            role="user",
            content="I need romantic date ideas in Ottawa"
        )
    ]
)

response = stub.Chat(iter([request]))
for chunk in response:
    print(chunk.content)
```

### Admin Web UI

Access at `http://localhost:8000` (or configured port).

**Features:**
- Navigate to "Add Date Idea" to create new entries
- Browse existing ideas
- Search by city, category, price tier
- View database statistics

## Development

### Project Structure

```
ai_orchestrator/
├── server/
│   ├── main.py              # gRPC server entry point
│   ├── chat_handler.py      # Chat request handler
│   ├── llm/
│   │   ├── engine.py        # LLM engine with tool calling
│   │   └── system_prompt.py # System prompt
│   ├── tools/
│   │   ├── agent_tools.py           # Google Places, Maps, web scraping
│   │   ├── vector_store.py          # Vector database interface
│   │   ├── chat_context_storage.py  # Chat history storage
│   │   ├── postgresql_vector_store.py # PostgreSQL implementation
│   │   └── web_search.py            # Web search tools
│   └── ...
├── web_ui.py            # Admin portal
├── setup.py             # Setup script
├── inspect_vector_store.py # Database inspection tool
├── requirements.txt     # Python dependencies
└── Makefile            # Build and run commands
```

### Available Make Commands

- `make help` - Show all available commands
- `make install` - Install dependencies
- `make setup` - Setup database and vector store
- `make start-server` - Start chat server
- `make web-ui` - Start admin web UI
- `make kill-server` - Stop all running servers
- `make inspect-db` - View database statistics
- `make clean` - Clean generated files
- `make test` - Run tests

### Adding New Date Ideas

**Via Web UI:**
1. Start the web UI: `make web-ui`
2. Navigate to "Add Date Idea"
3. Fill in the form and submit

**Via Python:**
```python
from server.tools.vector_store import get_vector_store

vector_store = get_vector_store()
await vector_store.add_date_idea(
    name="Romantic Dinner at The Whalesbone",
    description="Intimate seafood restaurant with fresh oysters",
    city="Ottawa",
    price_tier=3,
    duration_minutes=120,
    indoor=True,
    categories=["food", "romantic"],
    unique_features=["live_music"],
    is_featured=False
)
```

## Architecture

The system uses a multi-layered architecture:

1. **Client Layer**: gRPC clients (web, mobile, etc.)
2. **API Layer**: gRPC server with interceptors
3. **Handler Layer**: Chat request processing
4. **LLM Layer**: OpenAI integration with function calling
5. **Tools Layer**: Agent tools (search, maps, scraping)
6. **Storage Layer**: PostgreSQL with pgvector

### Agent Tools

The system includes 10+ agent tools automatically selected by the AI:

- `search_date_ideas` - Semantic search of curated ideas
- `search_featured_dates` - Find unique/special experiences
- `google_places_search` - Real-time venue discovery
- `find_nearby_venues` - Location-based recommendations
- `get_directions` - Travel planning
- `web_scrape_venue_info` - Detailed venue information
- `enhanced_web_search` - Specialized search
- `geocode_location` - Address conversion
- `web_search` - General web search

## Database Schema

### Main Tables

- `date_ideas` - Curated date idea database
- `date_idea_embeddings` - Vector embeddings for semantic search
- `chat_sessions` - Chat session tracking
- `chat_messages` - Message history with embeddings
- `chat_tool_calls` - Tool usage audit trail
- `chat_context_summaries` - Session summaries

## Troubleshooting

### Common Issues

**Database connection failed:**
- Ensure PostgreSQL is running
- Verify credentials in .env
- Install pgvector extension: `CREATE EXTENSION vector;`

**OpenAI API errors:**
- Check API key is valid
- Verify you have credits
- Check rate limits

**Vector store empty:**
- Run `make setup` to load sample data
- Add ideas via web UI
- Check database permissions

### Logs

Server logs are written to:
- Console output (stdout)
- `/tmp/ai_orchestrator.log`

Set log level in code or use:
```bash
export LOG_LEVEL=DEBUG
```

## Contributing

This is a specialized date planning system. Improvements welcome in:
- Additional agent tools
- Better prompts
- UI enhancements
- Performance optimizations

## License

MIT License - See LICENSE file for details
