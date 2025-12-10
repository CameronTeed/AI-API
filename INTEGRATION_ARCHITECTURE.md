# 🏗️ Three-Tier Integration Architecture

## Current Setup

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                           │
│                    web-app/                                     │
│  • React 19 + TypeScript                                        │
│  • Streaming chat via fetch API                                 │
│  • Firebase authentication                                      │
│  • Axios HTTP client                                            │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/REST
                         │ :8080 (Java BE)
                         │ :8081 (Streaming)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              BACKEND (Java Spring Boot)                         │
│                    api/                                         │
│  • Spring Boot 3.4.5                                            │
│  • gRPC client to Python AI                                     │
│  • Firebase auth validation                                     │
│  • SSE streaming to FE                                          │
│  • PostgreSQL database                                          │
└────────────────────────┬────────────────────────────────────────┘
                         │ gRPC
                         │ :50051 (Python AI)
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           AI ORCHESTRATOR (Python FastAPI/gRPC)                 │
│                ai_orchestrator/                                 │
│  • FastAPI REST API (:8000)                                     │
│  • gRPC server (:50051)                                         │
│  • 11 AI tools (search, scrape, web search, etc.)              │
│  • Vector store + PostgreSQL                                    │
│  • OpenAI LLM integration                                       │
└─────────────────────────────────────────────────────────────────┘
```

## Current Data Flow

1. **FE → Java BE**: POST `/api/ai/chat/stream` with message
2. **Java BE → Python AI**: gRPC `Chat()` bidirectional stream
3. **Python AI**: Processes with 11 tools, streams chunks
4. **Java BE → FE**: SSE events (status, chunk, final, error)

## Key Integration Points

### 1. Frontend (Next.js)
- **File**: `web-app/src/lib/api/streaming-chat.ts`
- **Endpoint**: `POST /api/ai/chat/stream`
- **Auth**: Firebase Bearer token
- **Response**: Server-Sent Events (SSE)

### 2. Java Backend
- **Controller**: `AiChatController.java`
- **Service**: `AiChatService.java`
- **gRPC Client**: `GrpcAiClient.java`
- **Ports**: 8080 (REST), 8081 (Streaming)

### 3. Python AI
- **gRPC Server**: `start_server.py`
- **REST API**: `start_api_server.py`
- **Port**: 50051 (gRPC), 8000 (REST)
- **Tools**: 11 active tools in `agent_tools.py`

## Configuration Files

| Component | Config File | Key Settings |
|-----------|------------|--------------|
| Java BE | `application.properties` | AI host, port, auth token |
| Python AI | `.env` | OpenAI key, DB URL, ports |
| Frontend | `envConfig.ts` | API base URL, Firebase config |

## Current Issues & Gaps

1. **Port Mismatch**: FE expects :8081, Java BE on :8080
2. **Timeout**: 5-minute timeout configured but may need tuning
3. **Error Handling**: Limited error propagation from Python → Java → FE
4. **Logging**: Inconsistent logging across tiers
5. **Health Checks**: No unified health check endpoint
6. **Rate Limiting**: Not implemented
7. **Caching**: Only in Python AI, not in Java BE

## Performance Metrics

- **FE → Java**: ~100ms (HTTP)
- **Java → Python**: ~50ms (gRPC)
- **Python Processing**: 2-10s (depends on tools)
- **Total**: 5-15s per request

## Next Steps

1. Fix port configuration
2. Add health check endpoints
3. Improve error handling
4. Add request/response logging
5. Implement caching in Java BE
6. Add rate limiting
7. Create integration tests

