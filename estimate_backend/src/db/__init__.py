"""
Database utilities package.

Exposes:
- engine, SessionLocal factory, and get_db dependency via session module.
- Base and metadata from models for migrations and table creation.
"""
from .session import engine, SessionLocal, get_db  # re-export for convenience
from .models import Base, metadata  # make metadata easily importable

__all__ = ["engine", "SessionLocal", "get_db", "Base", "metadata"]
