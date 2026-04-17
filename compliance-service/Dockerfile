FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev libffi-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
# WeasyPrint runtime deps (pango, cairo, gdk-pixbuf) + libpq for postgres
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libcairo2 libglib2.0-0 libffi8 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
RUN groupadd -r cmpsvc && useradd -r -g cmpsvc -d /app -s /sbin/nologin cmpsvc
COPY --chown=cmpsvc:cmpsvc . .
RUN mkdir -p /app/uploads/certificates && chown -R cmpsvc:cmpsvc /app/uploads
USER cmpsvc
EXPOSE 8005
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8005/health', timeout=3).read()" || exit 1
# Single uvicorn worker per container. Workers=2 forked the lifespan twice,
# which in turn spawned the dds polling loop twice per container; Cloud Run
# already fans out instances for us.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8005"]
