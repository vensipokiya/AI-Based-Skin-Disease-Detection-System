# ─────────────────────────────────────────────────────────────────────────────
# DermaCare AI — Dockerfile
# Python 3.10-slim base, multi-step dependency caching, non-root user
# ─────────────────────────────────────────────────────────────────────────────

# Stage 1: Base image with system dependencies
FROM python:3.10-slim AS base

# Metadata
LABEL maintainer="DermaCare AI Team"
LABEL description="AI-Based Skin Disease Detection System"
LABEL version="2.0.0"

# Prevent Python from writing .pyc files and enable log streaming
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system-level dependencies needed for MySQL connector & image libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Python dependency installation (cached separately for faster rebuilds)
# ─────────────────────────────────────────────────────────────────────────────
FROM base AS builder

WORKDIR /app

# Copy requirements first to cache pip layer (only re-runs on requirements change)
COPY backend/requirements.txt ./backend/requirements.txt

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# ─────────────────────────────────────────────────────────────────────────────
# Stage 3: Final runtime image
# ─────────────────────────────────────────────────────────────────────────────
FROM base AS runtime

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.10 /usr/local/lib/python3.10
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the full project (respects .dockerignore)
COPY . .

# Create a non-root user for security
RUN addgroup --system dermacare && \
    adduser --system --ingroup dermacare --no-create-home dermacare && \
    chown -R dermacare:dermacare /app

USER dermacare

# Expose the application port
EXPOSE 8000

# Health check — polls the root endpoint every 30s
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Start the application with Uvicorn
# Override with --workers flag via docker run if needed for production
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
