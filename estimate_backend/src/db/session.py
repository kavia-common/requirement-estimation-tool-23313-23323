"""Async database engine and session factory.

This module centralizes SQLAlchemy/SQLModel engine and session setup for the app.
It supports:
- Async engine using the configured DATABASE_URL
- AsyncSession factory via sessionmaker
- Helpers to create/drop tables (for bootstrap or tests)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

from .config import get_db_settings


# Lazy singletons
_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def _ensure_engine() -> AsyncEngine:
    """Create the async engine if not already created."""
    global _engine
    if _engine is None:
        settings = get_db_settings()
        _engine = create_async_engine(settings.database_url, echo=settings.db_echo)
    return _engine


def _ensure_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Ensure the async session maker exists."""
    global _session_maker
    if _session_maker is None:
        engine = _ensure_engine()
        _session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    return _session_maker


# PUBLIC_INTERFACE
@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession with proper cleanup.

    Usage:
        async with get_session() as session:
            ...

    Returns:
        An async generator yielding an AsyncSession instance.
    """
    maker = _ensure_sessionmaker()
    async with maker() as session:
        try:
            yield session
        finally:
            # session is closed by context manager
            ...


# PUBLIC_INTERFACE
async def init_db() -> None:
    """Initialize the database by creating all tables.

    Intended to be called on startup for dev/local usage. In production,
    prefer migrations (e.g., Alembic) to manage schema changes.
    """
    engine = _ensure_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


# PUBLIC_INTERFACE
async def drop_db() -> None:
    """Drop all database tables.

    Useful for testing or development resets. Use with caution.
    """
    engine = _ensure_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
