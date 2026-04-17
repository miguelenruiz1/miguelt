FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
RUN groupadd -r invsvc && useradd -r -g invsvc -d /app -s /sbin/nologin invsvc
COPY --chown=invsvc:invsvc . .
RUN mkdir -p /app/uploads/products && chown -R invsvc:invsvc /app/uploads
USER invsvc
EXPOSE 8003
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health', timeout=3).read()" || exit 1
# workers=1 because lifespan hosts daily expiry + reorder scanners. Multiple
# workers = duplicate scheduler (Redis leader lock mitigates but wastes CPU).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8003"]
