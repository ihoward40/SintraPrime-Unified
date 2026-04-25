# SintraPrime UniVerse — Python FastAPI Core
# Production multi-stage build

FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Also install FastAPI / uvicorn for serving
RUN pip install --no-cache-dir --user \
    fastapi>=0.104.0 \
    uvicorn[standard]>=0.24.0 \
    httpx>=0.25.0 \
    python-multipart>=0.0.6

# Production stage
FROM python:3.12-slim

# Security: Run as non-root user
RUN groupadd -r universe && useradd -r -g universe universe

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /home/universe/.local

# Set environment variables
ENV PATH=/home/universe/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    UNIVERSE_ENV=production

# Copy application code
COPY universe/ /app/universe/

# Copy entrypoint
COPY docker-entrypoint.py /app/docker-entrypoint.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Switch to non-root user
USER universe

# Expose port
EXPOSE 8080

# Run the FastAPI app via uvicorn
CMD ["python", "/app/docker-entrypoint.py"]
