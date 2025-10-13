# Getting Started with AI Date Ideas Orchestrator

## 5-Minute Quick Start

### 1. Install Dependencies
```bash
make install
```

### 2. Configure Environment
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys (at minimum, add OPENAI_API_KEY and database credentials)
nano .env
```

### 3. Setup Database
```bash
# Make sure PostgreSQL is running and create the database:
psql -U postgres -c "CREATE DATABASE ai_orchestrator;"
psql -U postgres -d ai_orchestrator -c "CREATE EXTENSION vector;"

# Run the setup script to initialize tables and load sample data
make setup
```

### 4. Start the Services

**Terminal 1 - Chat Server:**
```bash
make start-server
# or simply: make start
```

**Terminal 2 - Admin Web UI:**
```bash
make web-ui
```

### 5. Test It Out

**Web UI:** Open http://localhost:8000 in your browser to manage date ideas.

**Chat API:** Use a gRPC client to connect to `localhost:7000`

## What's Next?

- Add more date ideas through the web UI
- Customize the system prompt in `server/llm/system_prompt.py`
- Add your Google Places/Maps API keys for real-time venue search
- Explore the database with `make inspect-db`

## Common Commands

```bash
make help          # Show all available commands
make setup         # Setup database and load sample data
make start         # Start the chat server
make web-ui        # Start the admin web UI
make kill-server   # Stop all running servers
make clean         # Clean generated files
make inspect-db    # View database statistics
```

## Troubleshooting

### "Cannot connect to database"
- Ensure PostgreSQL is running: `systemctl status postgresql` or `brew services list`
- Check credentials in .env match your PostgreSQL setup
- Create the database if it doesn't exist

### "OPENAI_API_KEY not found"
- Make sure you've created a .env file (copy from .env.example)
- Add your OpenAI API key to the OPENAI_API_KEY variable
- The .env file should be in the ai_orchestrator directory

### "pgvector extension not found"
- Install pgvector in your PostgreSQL database:
  ```bash
  psql -U postgres -d ai_orchestrator -c "CREATE EXTENSION vector;"
  ```

### "Port already in use"
- Change the PORT in .env (default is 7000 for gRPC, 8000 for web UI)
- Or kill existing processes: `make kill-server`

## Need Help?

Check the full README.md for detailed documentation, architecture overview, and API examples.
