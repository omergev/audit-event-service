# --- Base Image ---
FROM python:3.10-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    curl ca-certificates netcat-traditional \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user early so we can assign ownership during COPY
RUN useradd -u 10001 -m appuser

# Install dependencies first for better layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
 && pip install -r /app/requirements.txt

# Copy application code with proper ownership (avoids chmod/chown errors later)
COPY --chown=10001:10001 . /app

# Drop privileges
USER appuser

ENV HOST=0.0.0.0 \
    PORT=8000 \
    UVICORN_WORKERS=1 \
    UVICORN_LOG_LEVEL=info

HEALTHCHECK --interval=30s --timeout=3s --retries=5 CMD nc -z 127.0.0.1 ${PORT} || exit 1
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host ${HOST} --port ${PORT} --workers ${UVICORN_WORKERS} --log-level ${UVICORN_LOG_LEVEL}"]
