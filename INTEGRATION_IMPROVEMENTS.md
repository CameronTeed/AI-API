# ✅ Integration Improvements Plan

## Phase 1: Critical Fixes (Do First)

### 1.1 Fix gRPC Port Configuration
**File**: `api/src/main/resources/application.yml`
```yaml
# BEFORE (line 54)
port: 7000

# AFTER
port: 50051
```

**File**: `ai_orchestrator/.env`
```bash
# BEFORE (line 32)
PORT=7000

# AFTER
PORT=50051
GRPC_PORT=50051
```

### 1.2 Fix IPv6/IPv4 Localhost
**File**: `api/src/main/resources/application.yml`
```yaml
# BEFORE (line 53)
host: "::1"

# AFTER
host: "localhost"
```

### 1.3 Add Health Check Endpoints

**Java BE** - Add to `AiChatController.java`:
```java
@GetMapping("/health")
public ResponseEntity<Map<String, String>> health() {
    return ResponseEntity.ok(Map.of(
        "status", "UP",
        "service", "AI Chat API",
        "timestamp", LocalDateTime.now().toString()
    ));
}
```

**Python AI** - Add to `server/api/app.py`:
```python
@app.get("/health")
async def health():
    return {
        "status": "UP",
        "service": "AI Orchestrator",
        "timestamp": datetime.now().isoformat()
    }
```

## Phase 2: Error Handling (High Priority)

### 2.1 Add Error Context to gRPC
**File**: `api/src/main/java/com/dateideas/api/service/AiChatService.java`

Add error details to response:
```java
if (error != null) {
    response.put("error", error);
    response.put("error_code", errorCode);
    response.put("error_details", errorDetails);
}
```

### 2.2 Propagate Errors to FE
**File**: `web-app/src/lib/api/streaming-chat.ts`

Parse error events with details:
```typescript
case 'error':
    const errorData = parsedData as any;
    onError(new Error(
        `${errorData.message} (${errorData.error_code})`
    ));
    return;
```

## Phase 3: Request Tracing (Medium Priority)

### 3.1 Add Correlation IDs
**Java BE**: Generate UUID for each request
**Python AI**: Accept and log correlation ID
**FE**: Include in all requests

```java
String correlationId = UUID.randomUUID().toString();
logger.info("[{}] Request started", correlationId);
```

## Phase 4: Timeout Alignment (Medium Priority)

**All tiers**: Set to 5 minutes (300 seconds)

```yaml
# Java
server:
  servlet:
    session:
      timeout: 300s
```

```python
# Python
TIMEOUT = 300  # 5 minutes
```

## Phase 5: Rate Limiting (Low Priority)

**Java BE**: Add Spring Security rate limiting
```java
@RateLimiter(limit = 10, period = 60)
@PostMapping("/chat/stream")
public void streamChat(...) { }
```

## Phase 6: Caching (Low Priority)

**Java BE**: Add response caching
```java
@Cacheable(value = "chatResponses", key = "#message")
public DateIdeaResponse getCompleteResponse(...) { }
```

## Implementation Order

1. ✅ Fix ports (5 min)
2. ✅ Fix localhost (2 min)
3. ✅ Add health checks (10 min)
4. ✅ Fix error handling (20 min)
5. ⏳ Add correlation IDs (15 min)
6. ⏳ Align timeouts (10 min)
7. ⏳ Add rate limiting (20 min)
8. ⏳ Add caching (15 min)

**Total Time**: ~90 minutes

## Testing After Each Phase

- Unit tests for each component
- Integration tests for FE ↔ Java ↔ Python
- End-to-end tests with real requests
- Load tests with concurrent requests

## Rollback Plan

Each change is isolated and can be reverted:
1. Config changes: Revert YAML/env files
2. Code changes: Git revert
3. Database: No schema changes needed

