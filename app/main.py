# app/main.py
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.database import engine
from app.routers import events, stream


app = FastAPI()
# Include the events router
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
