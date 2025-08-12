# syntax=docker/dockerfile:1.7

# --- Base Image ---
FROM python:3.10-slim AS base

# --- Environment hardening & Python runtime flags ---
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# --- System deps (minimal) ---
# NOTE: Add build deps here only if a package needs compilation (e.g., psycopg2==binary not used).
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    curl ca-certificates netcat-traditional \
 && rm -rf /var/lib/apt/lists/*

# --- Workdir & copy requirements first for better caching ---
WORKDIR /app

COPY requirements.txt /app/requirements.txt

# --- Install Python deps ---
# IMPORTANT: Prefer "psycopg[binary]" on Linux to avoid compiling libpq.
# If you add a new package:
#   pip install <package>==<version>
#   echo "<package>==<version>" >> requirements.txt
RUN pip install --upgrade pip setuptools wheel \
 && pip install -r /app/requirements.txt

# --- Copy application code ---
# NOTE: Update the path below if your package/module structure differs.
COPY . /app

# --- Non-root user for security ---
# NOTE: Make sure the UID/GID do not collide with mounted volumes on host.
RUN useradd -u 10001 -m appuser
USER appuser

# --- Default runtime configuration ---
# NOTE: You can override these via docker-compose or `docker run -e KEY=VALUE`.
ENV HOST=0.0.0.0 \
    PORT=8000 \
    UVICORN_WORKERS=1 \
    UVICORN_LOG_LEVEL=info

# --- Healthcheck (simple TCP) ---
# NOTE: Compose can also define a HTTP healthcheck on /health if available.
HEALTHCHECK --interval=30s --timeout=3s --retries=5 CMD nc -z 127.0.0.1 ${PORT} || exit 1

# --- Expose port & run ---
EXPOSE 8000

# NOTE: If your app entrypoint path is different, adjust `app.main:app`.
# For example, if your app module is "app.main" and ASGI object is "app":
CMD ["sh", "-c", "uvicorn app.main:app --host ${HOST} --port ${PORT} --workers ${UVICORN_WORKERS} --log-level ${UVICORN_LOG_LEVEL}"]
