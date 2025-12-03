# AI Orchestrator for Date Ideas

A comprehensive AI-powered system for generating, managing, and recommending date ideas. This system combines a gRPC backend, a REST API, and an Admin Web UI to provide intelligent, context-aware date recommendations using vector search, web scraping, and LLM reasoning.

## Features

*   **Intelligent Chat Agent**: Context-aware conversations with memory, capable of planning complex dates.
*   **Multi-Modal Search**: Combines vector database search (semantic), Google Places API (real-time location data), and web scraping (events/details).
*   **Parallel Tool Execution**: Optimized for performance with concurrent tool execution.
*   **Admin Web UI**: Manage date ideas, view stats, and manually scrape/import data.
*   **Dual API Support**:
    *   **gRPC**: High-performance streaming chat interface.
    *   **REST API**: Standard endpoints for chat, history, and admin management.
*   **Vector Database**: Semantic search for "romantic", "adventurous", etc. using embeddings.

## Architecture

The system is built with Python and consists of several key components:

*   **`server/`**: Core backend logic.
    *   **`llm/`**: LLM engine and reasoning agent (OpenAI GPT-4o).
    *   **`tools/`**: Tool implementations (Vector Store, Web Search, Google Places, etc.).
    *   **`api/`**: FastAPI REST endpoints.
    *   **`chat_handler.py`**: gRPC service implementation.
*   **`web_ui.py`**: FastAPI-based Admin Dashboard.
*   **`ai_orchestrator/`**: Main package directory.

## Prerequisites

*   Python 3.10+
*   PostgreSQL with `pgvector` extension.
*   API Keys:
    *   OpenAI API Key
    *   Google Places API Key (optional but recommended)
    *   SerpApi / Bing Search Key (optional for web search)

## Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd ai-api
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r ai_orchestrator/requirements.txt
    ```

3.  **Environment Setup**:
    Create a `.env` file in the root (or `ai_orchestrator/`) with the following:
    ```bash
    # Server
    PORT=7000
    API_PORT=8000
    
    # Database
    DB_HOST=localhost
    DB_PORT=5432
    DB_USER=postgres
    DB_PASSWORD=password
    DB_NAME=ai_orchestrator
    
    # AI / LLM
    OPENAI_API_KEY=sk-...
    
    # External Tools (Optional)
    GOOGLE_PLACES_API_KEY=...
    SERPAPI_API_KEY=...
    ```

4.  **Database Setup**:
    Ensure your PostgreSQL database is running and the schema is applied. You can use the `ai_orchestrator/sql/schema.sql` or Flyway migrations in `ai_orchestrator/flyway/`.

## Usage

### 1. Start the gRPC Chat Server
This is the main server for streaming chat interactions.
```bash
python3 ai_orchestrator/start_server.py
```

### 2. Start the REST API Server
Provides HTTP endpoints for chat and administration.
```bash
python3 ai_orchestrator/start_api_server.py
```
*   Swagger UI: `http://localhost:8000/docs`

### 3. Start the Admin Web UI
A visual interface to manage the database.
```bash
python3 ai_orchestrator/web_ui.py
```
*   Access at: `http://localhost:8000` (Note: Port might conflict if running both API and Web UI on default ports, configure `WEB_UI_PORT` if needed).

## Documentation

*   [Integration Guide](docs/INTEGRATION_GUIDE.md): Details on connecting to the gRPC service.

## Testing

Run the test suite:
```bash
cd ai_orchestrator
python3 -m pytest tests/
```
