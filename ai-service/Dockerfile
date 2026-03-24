FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd -r aisvc && useradd -r -g aisvc -d /app -s /sbin/nologin aisvc
COPY --chown=aisvc:aisvc . .

USER aisvc
EXPOSE 8006

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006", "--workers", "2"]
