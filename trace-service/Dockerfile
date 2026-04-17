# ─── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry==1.8.3

# Copy lockfile & pyproject first for layer caching
COPY pyproject.toml poetry.lock* ./

# Export requirements without dev deps
RUN poetry export --without dev --without-hashes -f requirements.txt -o requirements.txt

# ─── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Runtime deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Non-root user
RUN groupadd -r trace && useradd -r -g trace -d /app -s /sbin/nologin trace

# Copy application source
COPY --chown=trace:trace . .

# Switch to non-root
USER trace

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3).read()" || exit 1
# Default: API server (overridden in docker-compose for worker)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--http", "h11"]
