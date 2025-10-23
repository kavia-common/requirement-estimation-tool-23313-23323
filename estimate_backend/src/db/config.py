"""Database configuration and environment loading.

Loads database settings from environment variables with sensible defaults.
Do not hardcode configuration; use environment variables provided via .env.

Environment variables:
- DATABASE_URL: SQLAlchemy database URL. Default: sqlite+aiosqlite:///./data.db
- DB_ECHO: Whether to echo SQL statements (true/false). Default: false
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


@dataclass(frozen=True)
class DBSettings:
    """Immutable database settings parsed from environment variables."""

    database_url: str
    db_echo: bool

    @staticmethod
    # PUBLIC_INTERFACE
    def from_env(
        database_url_env: Optional[str] = None,
        db_echo_env: Optional[str] = None,
    ) -> "DBSettings":
        """Create DBSettings from environment variables.

        Args:
            database_url_env: Optional override value for the database URL.
            db_echo_env: Optional override value for the echo flag ("true"/"false").

        Returns:
            DBSettings: Parsed and validated settings object.
        """
        # Default to async SQLite with aiosqlite driver per requirements
        default_url = "sqlite+aiosqlite:///./data.db"

        raw_url = (
            database_url_env
            if database_url_env is not None
            else os.getenv("DATABASE_URL", default_url)
        )
        raw_echo = (
            db_echo_env if db_echo_env is not None else os.getenv("DB_ECHO", "false")
        )

        # Normalize boolean for echo
        echo = str(raw_echo).strip().lower() in {"1", "true", "yes", "y", "on"}

        return DBSettings(database_url=raw_url, db_echo=echo)


# PUBLIC_INTERFACE
def get_db_settings() -> DBSettings:
    """Get DB settings built from environment variables."""
    return DBSettings.from_env()
