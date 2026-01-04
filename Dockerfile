FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p /var/log/ai-orchestrator && chmod 755 /var/log/ai-orchestrator

# Expose ports
EXPOSE 50051 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('localhost', 50051), timeout=5)"

# Default environment variables for deployment
ENV PYTHONUNBUFFERED=1
ENV LOGGING_ENABLED=true
ENV LOGGING_LEVEL=INFO
ENV LOGGING_FILE=/var/log/ai-orchestrator/app.log
ENV DATABASE_URL=postgresql://postgres:postgres@postgres:5432/dateideas
ENV SENTRY_ENABLED=false
ENV ENVIRONMENT=production

# Start both gRPC and FastAPI servers
CMD ["python", "-m", "server.main"]

