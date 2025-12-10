# 🧪 Integration Testing Guide

## Quick Start - Test All Three Tiers

### Step 1: Start Python AI Orchestrator
```bash
cd ai_orchestrator
python3 start_server.py  # gRPC on :50051
python3 start_api_server.py  # REST on :8000
```

**Verify**:
```bash
curl http://localhost:8000/api/health/status
# Expected: {"status": "healthy", ...}
```

### Step 2: Start Java Backend
```bash
cd api
./gradlew bootRun
# Listens on :8081
```

**Verify**:
```bash
curl http://localhost:8081/api/ai/health
# Expected: {"status": "UP", ...}
```

### Step 3: Start Frontend
```bash
cd web-app
npm run dev
# Listens on :3000
```

**Verify**: Open http://localhost:3000 in browser

## Integration Tests

### Test 1: Python AI Health
```bash
curl -X GET http://localhost:8000/api/health/status
```

**Expected Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-10T...",
  "components": {
    "llm_engine": "healthy",
    "vector_store": "healthy",
    "web_client": "healthy",
    "agent_tools": "healthy",
    "chat_storage": "healthy"
  }
}
```

### Test 2: Java Backend Health
```bash
curl -X GET http://localhost:8081/api/ai/health
```

**Expected Response**:
```json
{
  "status": "UP",
  "service": "AI Chat API",
  "timestamp": "2025-12-10T...",
  "grpc_connected": true
}
```

### Test 3: Java → Python gRPC Connection
```bash
# Check logs for successful gRPC connection
tail -f api/logs/dateideas-api.log | grep "gRPC"
```

**Expected**: `✅ gRPC AI client initialized successfully`

### Test 4: End-to-End Chat Request
```bash
curl -X POST http://localhost:8081/api/ai/chat/stream \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -H "Accept: text/event-stream" \
  -d "message=Date ideas in Ottawa" \
  -d "location=Ottawa"
```

**Expected**: SSE stream with chunks

### Test 5: Frontend Streaming Chat
1. Open http://localhost:3000
2. Log in with Firebase
3. Type: "Date ideas in Ottawa"
4. Watch real-time streaming response

## Troubleshooting

### Issue: Java can't connect to Python
**Check**:
```bash
# Verify Python is listening on 50051
netstat -an | grep 50051
# or
lsof -i :50051
```

**Fix**: Ensure `PORT=50051` in `ai_orchestrator/.env`

### Issue: Frontend can't reach Java
**Check**:
```bash
curl http://localhost:8081/api/ai/health
```

**Fix**: Ensure `NEXT_PUBLIC_API_BASE_URL=http://localhost:8081` in `web-app/.env`

### Issue: gRPC connection timeout
**Check logs**:
```bash
tail -f api/logs/dateideas-api.log | grep "gRPC"
```

**Fix**: 
- Verify Python AI is running
- Check firewall allows port 50051
- Verify localhost resolution

### Issue: SSE stream not working
**Check**:
```bash
curl -v http://localhost:8081/api/ai/chat/stream
```

**Expected**: `Content-Type: text/event-stream`

## Performance Testing

### Load Test (10 concurrent requests)
```bash
for i in {1..10}; do
  curl -X POST http://localhost:8081/api/ai/chat \
    -d "message=Date ideas" &
done
wait
```

### Latency Test
```bash
time curl -X POST http://localhost:8081/api/ai/chat \
  -d "message=Date ideas"
```

**Expected**: 5-15 seconds total

## Monitoring

### Watch All Logs
```bash
# Terminal 1: Python AI
tail -f ai_orchestrator/logs/server.log

# Terminal 2: Java BE
tail -f api/logs/dateideas-api.log

# Terminal 3: Frontend
npm run dev
```

### Check Connections
```bash
# Active connections
netstat -an | grep ESTABLISHED | grep -E "8081|50051|8000"
```

## Success Criteria

✅ All health checks return UP/healthy
✅ Java connects to Python via gRPC
✅ Frontend connects to Java via HTTP
✅ Chat request completes in <15 seconds
✅ Streaming chunks arrive in real-time
✅ No errors in any logs
✅ Load test handles 10 concurrent requests

## Next Steps

If all tests pass:
1. Deploy to staging
2. Run integration tests in CI/CD
3. Monitor production metrics
4. Set up alerting for health checks

