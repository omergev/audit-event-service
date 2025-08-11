# tests/conftest.py
import os
import pytest
from fastapi.testclient import TestClient

# Ensure short interval/limit only for tests if needed (does not affect app code defaults).
os.environ.setdefault("RETENTION_YEARS", "3")
os.environ.setdefault("RETENTION_DELETE_LIMIT", "1000")
# We do not change RETENTION_INTERVAL_SECONDS for tests since we invoke deletion directly.

from app.main import app  # import after env is set
from app.database import engine

@pytest.fixture(scope="function")
def client():
    """A FastAPI TestClient for calling API endpoints."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def db_conn():
    """Yield a SQLAlchemy connection inside a transaction and roll it back after each test."""
    # Note: If your DB is shared across tests, prefer truncating test data explicitly.
    conn = engine.connect()
    trans = conn.begin()
    try:
        yield conn
    finally:
        trans.rollback()
        conn.close()
