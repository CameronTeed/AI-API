#!/usr/bin/env python3
"""
Simple start script for the AI Date Ideas Chat Server
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import and run the server
from server.main import main

if __name__ == '__main__':
    print("🚀 Starting AI Date Ideas Chat Server...")
    print("📝 Logs will be written to /tmp/ai_orchestrator.log")
    print("🔌 Server will listen on port 7000 (or PORT env var)")
    print("⚠️  Press Ctrl+C to stop\n")
    main()
