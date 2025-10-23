"""
Database seeding utility to populate initial reference data.

Seeds:
- RateCard: baseline roles and hourly rates (currency from env or default USD).
- ComplexityDefaults: default hours for item_type + complexity combinations.

Usage:
    python -m src.db.seed
or
    python requirement-estimation-tool-23313-23323/estimate_backend/src/db/seed.py

Environment:
- DATABASE_URL: database DSN (loaded via src.db.session); defaults to local SQLite file.
- DEFAULT_CURRENCY: optional, defaults to "USD".
"""
from __future__ import annotations

import os
from decimal import Decimal
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.session import engine, SessionLocal
from src.db.models import Base, RateCard, ComplexityDefaults


def _ensure_tables():
    """Create all tables if they don't exist yet."""
    Base.metadata.create_all(bind=engine)


def _upsert_rate_cards(db: Session, entries: Iterable[tuple[str, Decimal, str]]) -> None:
    """Insert rate card entries if missing; update if rate or currency changed."""
    for role, hourly_rate, currency in entries:
        existing = db.execute(select(RateCard).where(RateCard.role == role)).scalar_one_or_none()
        if existing:
            changed = False
            if Decimal(existing.hourly_rate) != hourly_rate:
                existing.hourly_rate = hourly_rate  # type: ignore[assignment]
                changed = True
            if existing.currency != currency:
                existing.currency = currency
                changed = True
            if changed:
                db.add(existing)
        else:
            db.add(RateCard(role=role, hourly_rate=hourly_rate, currency=currency))


def _upsert_complexity_defaults(db: Session, entries: Iterable[tuple[str, str, float]]) -> None:
    """Insert complexity defaults if missing; update default_hours if changed."""
    for item_type, complexity, default_hours in entries:
        existing = db.execute(
            select(ComplexityDefaults).where(
                (ComplexityDefaults.item_type == item_type)
                & (ComplexityDefaults.complexity == complexity)
            )
        ).scalar_one_or_none()
        if existing:
            if float(existing.default_hours) != float(default_hours):
                existing.default_hours = float(default_hours)
                db.add(existing)
        else:
            db.add(
                ComplexityDefaults(
                    item_type=item_type, complexity=complexity, default_hours=float(default_hours)
                )
            )


def run() -> None:
    """Run the seed operations in a single transaction."""
    _ensure_tables()

    default_currency = os.getenv("DEFAULT_CURRENCY", "USD")

    # Baseline illustrative data; adjust as needed in future passes.
    rate_cards = [
        ("developer", Decimal("120.00"), default_currency),
        ("qa", Decimal("90.00"), default_currency),
        ("pm", Decimal("130.00"), default_currency),
        ("designer", Decimal("110.00"), default_currency),
    ]

    complexity_defaults = [
        # item_type, complexity, default_hours
        ("frontend", "low", 4.0),
        ("frontend", "medium", 8.0),
        ("frontend", "high", 16.0),
        ("backend", "low", 6.0),
        ("backend", "medium", 12.0),
        ("backend", "high", 24.0),
        ("api", "low", 3.0),
        ("api", "medium", 6.0),
        ("api", "high", 12.0),
        ("general", "low", 2.0),
        ("general", "medium", 5.0),
        ("general", "high", 10.0),
    ]

    with SessionLocal() as db:
        with db.begin():
            _upsert_rate_cards(db, rate_cards)
            _upsert_complexity_defaults(db, complexity_defaults)


# PUBLIC_INTERFACE
def seed():
    """Seed the database with initial RateCard and ComplexityDefaults data."""
    run()


if __name__ == "__main__":
    run()
