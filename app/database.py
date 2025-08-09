from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL
import os

SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"

# createing the SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=SQL_ECHO, future=True, pool_pre_ping=True)

# creating a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)    

# Base class for ORM models
Base = declarative_base()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()