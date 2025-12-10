# 🧪 Testing Guide - Date Ideas AI Chat System

## Quick Start Testing

### 1. Start All Services

**Terminal 1 - Python AI**:
```bash
cd ai_orchestrator
python3 start_server.py &
python3 start_api_server.py
```

**Terminal 2 - Java Backend**:
```bash
cd api
./gradlew bootRun
```

**Terminal 3 - Frontend**:
```bash
cd web-app
npm run dev
```

---

## Manual Testing

### Test 1: Basic Chat Flow
1. Open http://localhost:3000
2. Log in with Firebase
3. Type: "Find me romantic date ideas in Ottawa"
4. Verify:
   - ✅ Message appears in chat
   - ✅ Loading indicator shows
   - ✅ AI response streams in real-time
   - ✅ Structured options appear with title, price, logistics
   - ✅ "View on Map" button works

---

### Test 2: Event Handling
Open browser DevTools (F12) → Console and verify events:

```javascript
// Should see in console:
// "Chunk received: {text: '...', isStructured: false, isDone: false}"
// "Final received: {text: '...', summary: '...', options: [...]}"
// "Stream complete: {status: 'completed', duration: 5234}"
```

**Expected Order**:
1. `session` event
2. `status` event
3. Multiple `chunk` events
4. `final` event (with structured answer)
5. `complete` event

---

### Test 3: Error Handling
1. Stop Java Backend
2. Try to send a message
3. Verify: Error message displays (not "currently not deployed")

---

### Test 4: Structured Answer Validation
Check Java Backend logs for:
```
✅ Final response ready - Text: XXX chars, Options: N
```

Verify options have:
- ✅ Non-empty title
- ✅ Non-empty logistics (or "Contact for details")
- ✅ Price field
- ✅ Categories

---

## Automated Testing

### Unit Tests
```bash
# Frontend
cd web-app
npm test

# Java Backend
cd api
./gradlew test

# Python AI
cd ai_orchestrator
pytest tests/
```

---

### Integration Tests
```bash
# Test complete flow
cd ai_orchestrator
pytest tests/test_chat_flow.py -v
```

---

## Performance Testing

### Measure Response Time
1. Open DevTools → Network tab
2. Send message
3. Check `/api/ai/chat/stream` request duration
4. Expected: 5-15 seconds depending on tools used

### Check Streaming Latency
```bash
# Monitor logs for chunk timing
grep "chunk" api/logs/application.log | head -20
```

---

## Debugging

### Enable Debug Logging

**Java Backend** (`application.yml`):
```yaml
logging:
  level:
    com.dateideas.api: DEBUG
```

**Python AI** (`.env`):
```
LOG_LEVEL=DEBUG
```

### Check Logs
```bash
# Java Backend
tail -f api/logs/application.log

# Python AI
tail -f ai_orchestrator/logs/app.log
```

---

## Checklist

- [ ] Frontend loads without errors
- [ ] Chat interface is responsive
- [ ] Messages stream in real-time
- [ ] Structured options display correctly
- [ ] Error messages are helpful
- [ ] No console errors in DevTools
- [ ] Java Backend logs show proper event flow
- [ ] Python AI logs show tool execution
- [ ] Response time is acceptable (< 20s)
- [ ] Options have all required fields

---

## Known Issues & Workarounds

**Issue**: Slow first response
- **Cause**: Cold start of Python AI
- **Workaround**: Send a test message first

**Issue**: Empty options appearing
- **Cause**: LLM returned incomplete data
- **Workaround**: Fixed in latest code (validates fields)


