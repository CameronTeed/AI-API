.PHONY: help install compile-protos test start-server clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements.txt

compile-protos:  ## Compile Protocol Buffer files
	python3 -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. protos/*.proto

test-setup:  ## Test the setup
	PYTHONPATH=. python3 test_setup.py

test:  ## Run tests
	pytest tests/ -v

test-enhanced:  ## Test enhanced chat system with agent tools
	PYTHONPATH=. python3 test_enhanced_system.py

start-server:  ## Start the AI Orchestrator server
	PYTHONPATH=. python3 -m server.main

start-enhanced:  ## Start the enhanced AI Orchestrator server with agent tools and chat storage
	PYTHONPATH=. python3 -m server.enhanced_main

example-client:  ## Run the example client (server must be running)
	PYTHONPATH=. python3 example_client.py

test-kill-client:  ## Test the KillChat and HealthCheck endpoints
	PYTHONPATH=. python3 test_kill_client.py

kill-server:  ## Kill any running AI Orchestrator server processes
	@echo "🔪 Killing AI Orchestrator server processes..."
	@pkill -f "python3 -m server.main" || echo "No server processes found"
	@pkill -f "python3 -m server.enhanced_main" || echo "No enhanced server processes found"
	@pkill -f "server.main\|server.enhanced_main" || echo "No additional server processes found"
	@echo "✅ Server kill command completed"

health-check:  ## Check if the server is healthy (requires grpcurl)
	@echo "🩺 Checking server health..."
	@grpcurl -plaintext localhost:7000 dateplanner.v1.AiOrchestrator/HealthCheck || echo "❌ Health check failed - server may not be running or grpcurl not installed"

setup-enhanced-chat:  ## Setup enhanced chat system with agent tools
	PYTHONPATH=. python3 setup_enhanced_chat.py

web-ui:  ## Start the web UI for data management
	PYTHONPATH=. python3 web_ui.py

explore-db:  ## Explore vector store contents interactively
	PYTHONPATH=. python3 explore_vector_store.py

inspect-db:  ## Inspect vector store statistics
	PYTHONPATH=. python3 inspect_vector_store.py

clean:  ## Clean generated files
	rm -f *_pb2.py *_pb2_grpc.py
	rm -rf __pycache__ server/__pycache__ server/tools/__pycache__ server/llm/__pycache__
	rm -rf .pytest_cache
	rm -f scraped_*.json simplified_*.json

setup: install compile-protos test-setup  ## Full setup (install, compile, test)

setup-enhanced: install compile-protos setup-enhanced-chat  ## Setup enhanced features with agent tools

dev: compile-protos start-server  ## Development mode (compile and start server)

dev-enhanced: compile-protos start-enhanced  ## Enhanced development mode (compile and start enhanced server)
