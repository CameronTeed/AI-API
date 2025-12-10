# 🚀 Quick Reference - Date Ideas AI Chat

## System Architecture
```
Frontend (Next.js 3000)
    ↓ HTTP/REST
Java Backend (Spring Boot 8081)
    ↓ gRPC
Python AI (FastAPI 50051)
```

---

## Starting the System

### Terminal 1: Python AI
```bash
cd ai_orchestrator
python3 start_server.py &
python3 start_api_server.py
```

### Terminal 2: Java Backend
```bash
cd api
./gradlew bootRun
```

### Terminal 3: Frontend
```bash
cd web-app
npm run dev
```

### Access
- Frontend: http://localhost:3000
- Java Backend: http://localhost:8081
- Python AI: http://localhost:8000

---

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ai/chat/stream` | POST | Stream chat responses |
| `/api/ai/chat` | POST | Get complete response |
| `/api/ai/health` | GET | Health check |
| `/api/health/status` | GET | Python AI health |

---

## Event Flow

```
Frontend sends message
    ↓
Java Backend receives POST /api/ai/chat/stream
    ↓
Java calls gRPC Chat() to Python AI
    ↓
Python AI executes tools and LLM
    ↓
Python sends ChatDelta events (text chunks)
    ↓
Java converts to SSE events
    ↓
Frontend receives SSE events:
  - session: Session ID
  - status: Connection status
  - chunk: Text chunks
  - final: Structured answer
  - complete: Stream finished
    ↓
Frontend renders chat with options
```

---

## Testing Checklist

- [ ] Frontend loads at http://localhost:3000
- [ ] Can log in with Firebase
- [ ] Can send a message
- [ ] Response streams in real-time
- [ ] Options display with title, price, logistics
- [ ] "View on Map" button works
- [ ] Error messages are helpful
- [ ] No console errors in DevTools

---

## Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| "Connection refused" | Start all 3 services |
| Empty options | Python AI field validation (FIXED) |
| Slow first response | Cold start - send test message |
| No streaming | Check Java Backend logs |
| Auth errors | Check Firebase config |

---

## Files Modified (Code Review)

1. **Frontend**: `web-app/src/app/components/chat/ChatInterface.tsx`
   - Added `complete` event handler
   - Fixed error message handling

2. **Java Backend**: `api/src/main/java/com/dateideas/api/controller/AiChatController.java`
   - Fixed event ordering
   - Removed duplicate events

3. **Python AI**: `ai_orchestrator/server/chat_handler.py`
   - Added field validation
   - Added default values

---

## Documentation Files

- `CODE_REVIEW.md` - Detailed analysis
- `FIXES_APPLIED.md` - What was fixed
- `TESTING_GUIDE.md` - How to test
- `FINAL_REVIEW_REPORT.md` - Executive summary
- `QUICK_REFERENCE.md` - This file

---

## Performance Targets

- Simple chat: 5-10 seconds
- With tools: 10-15 seconds
- Streaming latency: <100ms
- First chunk: 1-2 seconds

---

## Next Steps

1. ✅ Review CODE_REVIEW.md
2. ✅ Review FIXES_APPLIED.md
3. Run integration tests
4. Monitor logs during testing
5. Load test the system

---

## Support

For issues or questions:
1. Check logs: `tail -f api/logs/application.log`
2. Check DevTools console (F12)
3. Review TESTING_GUIDE.md
4. Check CODE_REVIEW.md for known issues


