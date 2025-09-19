# Java Backend Session Management Guide

## Overview
The gRPC service now supports session-based tracking for chat conversations. Here's how your Java backend should handle sessions:

## 1. Session ID Flow

### Client-Side (Java Backend → Python AI Service)
```java
// Generate a unique session ID for each chat conversation
String sessionId = UUID.randomUUID().toString();

// When creating a ChatRequest, include the session ID
ChatRequest request = ChatRequest.newBuilder()
    .setSessionId(sessionId)
    .addMessages(ChatMessage.newBuilder()
        .setRole("user")
        .setContent("Plan a date in San Francisco")
        .build())
    .setUserLocation(UserLocation.newBuilder()
        .setLat(37.7749)
        .setLon(-122.4194)
        .build())
    .build();
```

### Response Handling
```java
// All ChatDelta responses will include the session ID
responseObserver = new StreamObserver<ChatDelta>() {
    @Override
    public void onNext(ChatDelta delta) {
        String sessionId = delta.getSessionId();
        // Use sessionId to route response to correct client/conversation
        
        if (delta.getDone()) {
            // Session completed
            cleanupSession(sessionId);
        } else if (!delta.getTextDelta().isEmpty()) {
            // Stream text to client identified by sessionId
            sendToClient(sessionId, delta.getTextDelta());
        } else if (delta.hasStructured()) {
            // Send structured data to client
            sendStructuredToClient(sessionId, delta.getStructured());
        }
    }
    
    @Override
    public void onError(Throwable t) {
        // Handle error, cleanup session
        cleanupSession(sessionId);
    }
    
    @Override
    public void onCompleted() {
        // Session completed normally
        cleanupSession(sessionId);
    }
};
```

## 2. Session Management in Java Backend

### Session Storage
```java
@Component
public class ChatSessionManager {
    
    // Track active sessions
    private final Map<String, ChatSession> activeSessions = new ConcurrentHashMap<>();
    
    public static class ChatSession {
        private final String sessionId;
        private final String userId;  // Your app's user ID
        private final LocalDateTime startTime;
        private StreamObserver<ChatDelta> responseObserver;
        private StreamObserver<ChatRequest> requestObserver;
        
        // Constructor, getters, setters...
    }
    
    public String startChatSession(String userId) {
        String sessionId = UUID.randomUUID().toString();
        ChatSession session = new ChatSession(sessionId, userId, LocalDateTime.now());
        activeSessions.put(sessionId, session);
        return sessionId;
    }
    
    public void endChatSession(String sessionId) {
        activeSessions.remove(sessionId);
    }
    
    public ChatSession getSession(String sessionId) {
        return activeSessions.get(sessionId);
    }
    
    public boolean isSessionActive(String sessionId) {
        return activeSessions.containsKey(sessionId);
    }
}
```

### Integration with Your REST API
```java
@RestController
@RequestMapping("/api/chat")
public class ChatController {
    
    @Autowired
    private ChatSessionManager sessionManager;
    
    @Autowired
    private AiOrchestratorGrpcClient aiClient;
    
    // Start a new chat session
    @PostMapping("/start")
    public ResponseEntity<ChatStartResponse> startChat(@RequestBody ChatStartRequest request) {
        String sessionId = sessionManager.startChatSession(request.getUserId());
        return ResponseEntity.ok(new ChatStartResponse(sessionId));
    }
    
    // Send a message in an existing session
    @PostMapping("/message/{sessionId}")
    public ResponseEntity<Void> sendMessage(
            @PathVariable String sessionId,
            @RequestBody ChatMessageRequest request) {
        
        if (!sessionManager.isSessionActive(sessionId)) {
            return ResponseEntity.notFound().build();
        }
        
        // Forward to AI service with session ID
        aiClient.sendMessage(sessionId, request.getMessage(), request.getConstraints());
        return ResponseEntity.accepted().build();
    }
    
    // Kill a chat session
    @DeleteMapping("/kill/{sessionId}")
    public ResponseEntity<KillResponse> killChat(
            @PathVariable String sessionId,
            @RequestParam(required = false) String reason) {
        
        try {
            // Call gRPC KillChat endpoint
            KillChatRequest killRequest = KillChatRequest.newBuilder()
                .setSessionId(sessionId)
                .setReason(reason != null ? reason : "User terminated chat")
                .build();
            
            KillChatResponse response = aiClient.killChat(killRequest);
            
            // Clean up local session
            sessionManager.endChatSession(sessionId);
            
            return ResponseEntity.ok(new KillResponse(response.getSuccess(), response.getMessage()));
            
        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                .body(new KillResponse(false, "Failed to kill session: " + e.getMessage()));
        }
    }
}
```

## 3. WebSocket Integration for Real-time Streaming

### WebSocket Handler
```java
@Component
public class ChatWebSocketHandler extends TextWebSocketHandler {
    
    @Autowired
    private ChatSessionManager sessionManager;
    
    // Map WebSocket sessions to chat sessions
    private final Map<String, String> webSocketToChatSession = new ConcurrentHashMap<>();
    
    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        // Extract user info from session
        String userId = getUserIdFromSession(session);
        
        // Start a new chat session
        String chatSessionId = sessionManager.startChatSession(userId);
        webSocketToChatSession.put(session.getId(), chatSessionId);
        
        // Send session ID to client
        session.sendMessage(new TextMessage(
            "{\"type\":\"session_started\",\"sessionId\":\"" + chatSessionId + "\"}"
        ));
    }
    
    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String chatSessionId = webSocketToChatSession.get(session.getId());
        
        if (chatSessionId != null) {
            // Parse message and forward to AI service
            // The AI service will stream responses back via the gRPC response observer
        }
    }
    
    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        String chatSessionId = webSocketToChatSession.remove(session.getId());
        
        if (chatSessionId != null) {
            // Kill the chat session
            sessionManager.endChatSession(chatSessionId);
            // Optionally call gRPC KillChat endpoint
        }
    }
    
    // Method to send AI responses to WebSocket client
    public void sendToWebSocketClient(String chatSessionId, String message) {
        // Find WebSocket session by chat session ID and send message
        webSocketToChatSession.entrySet().stream()
            .filter(entry -> entry.getValue().equals(chatSessionId))
            .findFirst()
            .ifPresent(entry -> {
                // Send message to WebSocket client
            });
    }
}
```

## 4. Key Points for Implementation

1. **Session ID Generation**: Always generate unique session IDs (UUID recommended)
2. **Session Lifecycle**: Track session start/end times and clean up properly
3. **Error Handling**: Use KillChat endpoint when sessions error out
4. **Concurrent Access**: Use thread-safe collections for session storage
5. **Timeout Management**: Consider implementing session timeouts
6. **Monitoring**: Track active session count for health monitoring

## 5. Database Schema (Optional)

If you want to persist chat sessions:

```sql
CREATE TABLE chat_sessions (
    session_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NULL,
    status ENUM('active', 'completed', 'killed', 'error') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE chat_messages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    role ENUM('user', 'assistant', 'system') NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
);
```

## 6. Testing the Kill Functionality

You can test the kill functionality using the provided test client:
```bash
cd /home/cameron/ai-api/ai_orchestrator
make test-kill-client
```

This approach gives you full control over session management while leveraging the AI service's session tracking capabilities.