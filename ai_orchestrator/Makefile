.PHONY: help install setup compile-protos test start-server kill-server web-ui clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements.txt

setup:  ## Setup database and vector store
	PYTHONPATH=. python3 setup.py

compile-protos:  ## Compile Protocol Buffer files
	python3 -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. protos/*.proto

test:  ## Run tests
	pytest tests/ -v

start-server:  ## Start the AI Orchestrator chat server
	PYTHONPATH=. python3 -m server.main

start:  ## Start the chat server (alias for start-server)
	make start-server

kill-server:  ## Kill any running AI Orchestrator server processes
	@echo "🔪 Killing AI Orchestrator server processes..."
	@pkill -f "python3 -m server.main" || echo "No server processes found"
	@pkill -f "python3 web_ui.py" || echo "No web UI processes found"
	@echo "✅ Server kill command completed"

health-check:  ## Check if the server is healthy (requires grpcurl)
	@echo "🩺 Checking server health..."
	@grpcurl -plaintext localhost:7000 dateplanner.v1.AiOrchestrator/HealthCheck || echo "❌ Health check failed - server may not be running or grpcurl not installed"

web-ui:  ## Start the admin web UI for managing date ideas
	PYTHONPATH=. python3 web_ui.py

inspect-db:  ## Inspect vector store statistics
	PYTHONPATH=. python3 inspect_vector_store.py

clean:  ## Clean generated files and caches
	rm -f *_pb2.py *_pb2_grpc.py
	rm -rf __pycache__ server/__pycache__ server/tools/__pycache__ server/llm/__pycache__
	rm -rf .pytest_cache tests/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

dev:  ## Development mode (compile protos and start server)
	make compile-protos && make start-server
