# Backend/Frontend Integration Guide

This guide details how to integrate the Frontend (FE) with the AI Orchestrator Backend (BE).

## Service Overview

The AI Orchestrator exposes a **gRPC** service defined in `chat_service.proto`.
*   **Service Name**: `AiOrchestrator`
*   **Package**: `dateplanner.v1`
*   **Default Port**: `7000` (configurable via `PORT` env var)

## Connection Details

*   **Protocol**: gRPC (HTTP/2)
*   **Authentication**: Bearer Token (optional/configurable)
    *   Header: `Authorization: Bearer <token>`
    *   Token is set via `AI_BEARER_TOKEN` env var on the backend.

## API Methods

### 1. Chat (Streaming)

The primary interaction method. It uses a bidirectional stream, but logically follows a request-response stream pattern.

**RPC Signature:**
```protobuf
rpc Chat(stream ChatRequest) returns (stream ChatDelta);
```

**Flow:**
1.  **FE** opens the stream.
2.  **FE** sends a single `ChatRequest` message.
3.  **BE** streams back multiple `ChatDelta` messages.
4.  **BE** closes the stream when finished (or FE can cancel).

**Request Structure (`ChatRequest`):**
*   `session_id` (string): **CRITICAL**. A unique ID for the conversation.
    *   *Recommendation*: Generate a UUID on the FE for a new chat and persist it.
    *   Reuse this ID for follow-up messages in the same conversation context.
*   `messages` (List[`ChatMessage`]): The conversation history (or just the latest message).
    *   `role`: "user"
    *   `content`: The user's prompt.
*   `constraints` (Optional): Filter criteria (City, Budget, etc.).
*   `userLocation` (Optional): Lat/Lon for location-based results.

**Response Structure (`ChatDelta`):**
The BE streams these messages as chunks of data become available.
*   `text_delta` (string): A chunk of the natural language response. Append this to the UI display in real-time.
*   `structured` (`StructuredAnswer`): Sent **once** when the AI has formulated concrete recommendations.
    *   Contains a list of `Option` objects (Title, Price, Logistics, etc.).
    *   Render these as rich cards in the UI.
*   `done` (bool): If `true`, the response is complete.

### 2. KillChat

Terminates an active generation or session.

**RPC Signature:**
```protobuf
rpc KillChat(KillChatRequest) returns (KillChatResponse);
```

*   **Usage**: Call this when the user clicks "Stop Generating" or navigates away.
*   **Behavior**: The backend will flag the session as inactive in the database. Any running generation loop on any server instance will detect this flag and abort execution.

### 3. GetChatHistory

Retrieves past messages for a session.

**RPC Signature:**
```protobuf
rpc GetChatHistory(ChatHistoryRequest) returns (ChatHistoryResponse);
```

*   **Usage**: Call this when loading a previous conversation.
*   **Parameters**: `session_id` (required).

### 4. HealthCheck

Verifies backend status.

**RPC Signature:**
```protobuf
rpc HealthCheck(HealthCheckRequest) returns (HealthCheckResponse);
```

*   **Usage**: Load balancers or status pages.

## Integration Best Practices

### Session Management (Stateless Architecture)
The backend is designed to be stateless.
*   **FE Responsibility**: The Frontend MUST generate and manage the `session_id`.
*   **Persistence**: The backend stores chat history in a database keyed by `session_id`.
*   **Scaling**: You can route requests to any backend instance. The `session_id` ensures context is retrieved from the shared database.

### Handling the Stream
1.  **Initialize**: Connect to `AiOrchestrator`.
2.  **Send**: Write the `ChatRequest` to the stream.
3.  **Listen**: Loop over the incoming `ChatDelta` stream.
    *   If `text_delta` is present: Append to the "Assistant" message bubble.
    *   If `structured` is present: Render the recommendation cards (e.g., below the text).
    *   If `done` is true: Close the stream and enable the input field.

### Error Handling
*   Handle gRPC status codes (e.g., `UNAVAILABLE` if the server is down).
*   If the stream breaks, you can retry by sending the full message history in a new `ChatRequest` with the same `session_id`.

## Example Payload (JSON Representation)

**ChatRequest:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    { "role": "user", "content": "Find me a romantic dinner spot in Ottawa" }
  ],
  "constraints": {
    "city": "Ottawa",
    "budgetTier": 3
  }
}
```

**ChatDelta (Text Chunk):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "text_delta": "I found some great "
}
```

**ChatDelta (Structured Data):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "structured": {
    "summary": "Here are top picks:",
    "options": [
      {
        "title": "Riviera",
        "price": "$$$",
        "logistics": "62 Sparks St"
      }
    ]
  }
}
```
