"""
Database utilities package.

Exposes:
- engine, SessionLocal factory, and get_db dependency via session module.
"""
from .session import engine, SessionLocal, get_db  # re-export for convenience

__all__ = ["engine", "SessionLocal", "get_db"]
