# app/main.py

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.database import engine
from app.retention import RetentionService
from app.routers import events, stream
from app.config import RETENTION_INTERVAL_SECONDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

retention_service = RetentionService(RETENTION_INTERVAL_SECONDS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: start retention worker
    await retention_service.start()
    try:
        yield
    finally:
        # Shutdown: stop retention worker
        await retention_service.stop()

app = FastAPI(lifespan=lifespan)
app.include_router(events.router)
app.include_router(stream.router)

@app.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except SQLAlchemyError as e:
        return {"status": "error", "db": str(e)}
