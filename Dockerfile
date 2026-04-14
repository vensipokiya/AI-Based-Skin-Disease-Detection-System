# ─────────────────────────────────────────────────────────────────────────────
# DermaCare AI — Dockerfile
# Python 3.10-slim base · multi-stage build · non-root user · health check
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: base image with OS-level deps ────────────────────────────────────
FROM python:3.10-slim AS base

LABEL maintainer="DermaCare AI Team"
LABEL description="AI-Based Skin Disease Detection System"
LABEL version="2.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Stage 2: install Python dependencies (cached layer) ──────────────────────
FROM base AS builder

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# ── Stage 3: final runtime image ─────────────────────────────────────────────
FROM base AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.10 /usr/local/lib/python3.10
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy entire project (respects .dockerignore)
COPY . .

# Non-root user for security
RUN addgroup --system dermacare && \
    adduser --system --ingroup dermacare --no-create-home dermacare && \
    chown -R dermacare:dermacare /app

USER dermacare

EXPOSE 8000

# Health check — polls root endpoint every 30 s
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Start Uvicorn (override --workers via docker run for production)
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
