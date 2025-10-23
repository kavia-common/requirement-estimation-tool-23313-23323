import os
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Load environment variables from a .env file if present.
# This allows configuration without hard-coding values.
load_dotenv()

# Resolve DATABASE_URL and provide a sane default for local development.
# Default is a SQLite file in the project directory.
DEFAULT_SQLITE_URL = "sqlite:///./estimates.db"
DATABASE_URL: str = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)

# If using SQLite, ensure proper connection args for thread safety in SQLAlchemy.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Create the SQLAlchemy engine. We use synchronous engine for simplicity.
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Create a configured "Session" class and a session factory.
SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)

# PUBLIC_INTERFACE
def get_db() -> Generator[Session, None, None]:
    """Yield a database session for FastAPI dependency injection.

    This function is intended to be used with FastAPI's Depends system:

        from fastapi import Depends
        from sqlalchemy.orm import Session
        from src.db.session import get_db

        @app.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...

    Yields:
        A SQLAlchemy ORM Session bound to the configured engine.
    Ensures:
        The session is properly closed after the request lifecycle.
    """
    db: Optional[Session] = None
    try:
        db = SessionLocal()
        yield db
    finally:
        if db is not None:
            db.close()
