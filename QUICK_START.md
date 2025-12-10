# 🚀 Quick Start - Run the Full System

## Prerequisites
- Python 3.10+
- Java 21
- Node.js 18+
- PostgreSQL (Supabase)
- Firebase project

## One-Command Setup (3 Terminals)

### Terminal 1: Python AI Orchestrator
```bash
cd ai_orchestrator
python3 start_server.py &
python3 start_api_server.py
```

**Expected Output**:
```
✅ gRPC server listening on 0.0.0.0:50051
✅ FastAPI server listening on 0.0.0.0:8000
```

### Terminal 2: Java Backend
```bash
cd api
./gradlew bootRun
```

**Expected Output**:
```
✅ Started ApiApplication in X seconds
✅ gRPC AI client initialized successfully
```

### Terminal 3: Frontend
```bash
cd web-app
npm run dev
```

**Expected Output**:
```
✅ Ready in X ms
✅ Local: http://localhost:3000
```

## Verify Everything Works

### Check Health Endpoints
```bash
# Python AI
curl http://localhost:8000/api/health/status

# Java Backend
curl http://localhost:8081/api/ai/health

# Frontend
open http://localhost:3000
```

### Test Chat Flow
1. Open http://localhost:3000
2. Log in with Firebase
3. Type: "Date ideas in Ottawa"
4. Watch real-time streaming response

## Ports Reference

| Service | Port | Type |
|---------|------|------|
| Frontend | 3000 | HTTP |
| Java BE REST | 8081 | HTTP |
| Java BE gRPC | 9090 | gRPC |
| Python REST | 8000 | HTTP |
| Python gRPC | 50051 | gRPC |

## Troubleshooting

### Python AI won't start
```bash
# Check if port 50051 is in use
lsof -i :50051

# Kill process if needed
kill -9 <PID>
```

### Java can't connect to Python
```bash
# Verify Python is listening
netstat -an | grep 50051

# Check Java logs
tail -f api/logs/dateideas-api.log | grep gRPC
```

### Frontend can't reach Java
```bash
# Verify Java is running
curl http://localhost:8081/api/ai/health

# Check NEXT_PUBLIC_API_BASE_URL in web-app/.env
cat web-app/.env | grep API_BASE_URL
```

## Environment Variables

### Python AI (ai_orchestrator/.env)
```
OPENAI_API_KEY=sk-...
PORT=50051
GRPC_PORT=50051
DB_HOST=aws-1-ca-central-1.pooler.supabase.com
DB_USER=postgres.ylstfipwjgvyjqaadqbn
DB_PASSWORD=xMDEIKpvsNA8XRQM
```

### Java Backend (api/src/main/resources/application.yml)
```yaml
ai:
  orchestrator:
    host: localhost
    port: 50051
    bearer-token: development-token-123
```

### Frontend (web-app/.env)
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8081
NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSy...
```

## Performance Tips

1. **Parallel Tool Execution**: Already enabled in Python AI
2. **Caching**: 5-minute cache for tool results
3. **Connection Pooling**: Configured for PostgreSQL
4. **Streaming**: Real-time SSE from Java to Frontend

## Next Steps

1. ✅ Run all three services
2. ✅ Verify health endpoints
3. ✅ Test chat functionality
4. ✅ Check logs for errors
5. ⏳ Deploy to staging
6. ⏳ Run load tests
7. ⏳ Deploy to production

## Support

See detailed docs:
- `INTEGRATION_ARCHITECTURE.md` - System design
- `INTEGRATION_TESTING_GUIDE.md` - Testing procedures
- `INTEGRATION_COMPLETE.md` - Full integration status

