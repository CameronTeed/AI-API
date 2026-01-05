# Build stage - Install dependencies
FROM python:3.10-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements-base.txt requirements-ml.txt ./

# Install base dependencies first (faster, no compilation needed)
RUN pip install --no-cache-dir \
    --disable-pip-version-check \
    -q \
    -r requirements-base.txt

# Install ML dependencies separately (slower, but isolated)
# Use --no-build-isolation for faster compilation
RUN pip install --no-cache-dir \
    --no-build-isolation \
    --disable-pip-version-check \
    -q \
    -r requirements-ml.txt

# Runtime stage - Minimal image
FROM python:3.10-slim

WORKDIR /app

# Install only runtime dependencies (no build tools)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p /var/log/ai-orchestrator && chmod 755 /var/log/ai-orchestrator

# Expose ports
EXPOSE 50051 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

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

