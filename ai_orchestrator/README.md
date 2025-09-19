# AI Orchestrator Service

Python 3.11+ gRPC service that acts as the AI orchestrator for a "Date Planner" chatbot.

## Features

- **Bidirectional streaming chat** via gRPC
- **Database integration** with Java backend via gRPC
- **Web search fallback** using SerpAPI or Bing
- **LLM tool calling** with OpenAI for intelligent decision making
- **Bearer token authentication**
- **Structured response format** with citations

## Architecture

```
Frontend -> AI Orchestrator (Python) -> Java Backend (Database)
                                     -> Web Search (SerpAPI/Bing)
                                     -> OpenAI (LLM)
```

## Environment Variables

```bash
# Required
OPENAI_API_KEY=your_openai_key

# Optional
SEARCH_PROVIDER=serpapi|bing
SEARCH_API_KEY=your_search_api_key
JAVA_GRPC_TARGET=localhost:9090
AI_BEARER_TOKEN=your_bearer_token
DEFAULT_CITY=Ottawa
PORT=7000
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Compile Protocol Buffers:**
   ```bash
   python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. protos/*.proto
   ```

3. **Set environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Run the server:**
   ```bash
   python -m ai_orchestrator.server.main
   ```

## Protocol Buffers

The service defines two main proto files:

- `protos/chat_service.proto` - AI orchestrator service (this service)
- `protos/date_ideas_service.proto` - Java backend service (client)

## Usage Example

### Python Client

```python
import grpc
import chat_service_pb2
import chat_service_pb2_grpc

# Create channel with auth
channel = grpc.insecure_channel('localhost:7000')
metadata = [('authorization', 'Bearer your_bearer_token')]

stub = chat_service_pb2_grpc.AiOrchestratorStub(channel)

# Create request
request = chat_service_pb2.ChatRequest(
    messages=[
        chat_service_pb2.ChatMessage(
            role="user",
            content="I want romantic date ideas in Ottawa under $100"
        )
    ],
    constraints=chat_service_pb2.Constraints(
        city="Ottawa",
        budgetTier=2,
        hours=180,
        categories=["Romantic"]
    ),
    stream=True
)

# Stream responses
for response in stub.Chat(iter([request]), metadata=metadata):
    if response.text_delta:
        print(response.text_delta, end='')
    if response.structured:
        print(f"\nStructured answer: {response.structured}")
    if response.done:
        break
```

## Testing

Run tests with pytest:

```bash
pytest tests/
```

## Project Structure

```
ai_orchestrator/
├── protos/
│   ├── chat_service.proto
│   └── date_ideas_service.proto
├── server/
│   ├── __init__.py
│   ├── main.py                 # Server bootstrap
│   ├── interceptors.py         # Auth & logging
│   ├── chat_handler.py         # Chat service implementation
│   ├── schemas.py              # Pydantic models
│   ├── utils.py                # Helper functions
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── db_client.py        # Java gRPC client
│   │   └── web_search.py       # SerpAPI/Bing client
│   └── llm/
│       ├── __init__.py
│       ├── engine.py           # OpenAI integration
│       └── system_prompt.py    # LLM prompts
├── tests/
│   ├── test_db_client.py
│   └── test_chat_flow.py
├── requirements.txt
└── README.md
```

## Development

1. **Compile protos after changes:**
   ```bash
   python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. protos/*.proto
   ```

2. **Run with auto-reload during development:**
   ```bash
   python -m ai_orchestrator.server.main
   ```

3. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

## TODO

- [ ] Add TLS support for production
- [ ] Implement health checks
- [ ] Add metrics and monitoring
- [ ] Add rate limiting
- [ ] Add request/response caching
- [ ] Add more comprehensive error handling
- [ ] Add support for multiple LLM providers

## License

MIT License
