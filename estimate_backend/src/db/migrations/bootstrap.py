"""Bootstrap database seed script.

Inserts initial data if tables are empty:
- Settings: default hourly rate
- RequirementCatalog: a small starter catalog

This script is idempotent: it checks for existing records before inserting.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import RequirementCatalog, Settings


DEFAULT_HOURLY_RATE = 120.0  # USD; can be overridden later via API/admin
DEFAULT_RATE_KEY = "default_hourly_rate"


async def _ensure_default_settings(session: AsyncSession) -> None:
    """Ensure default settings exist."""
    # Check if the default rate setting exists
    result = await session.execute(
        select(Settings).where(Settings.key == DEFAULT_RATE_KEY)
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        session.add(
            Settings(
                key=DEFAULT_RATE_KEY,
                value=str(DEFAULT_HOURLY_RATE),
                description="Default hourly rate applied when an estimate does not specify a rate.",
            )
        )


async def _ensure_catalog_seed(session: AsyncSession) -> None:
    """Ensure a minimal requirement catalog exists."""
    # Check if any catalog items exist
    count_result = await session.execute(select(func.count(RequirementCatalog.id)))
    total = count_result.scalar_one() or 0
    if total > 0:
        return

    seed_items: Sequence[RequirementCatalog] = [
        RequirementCatalog(
            key="discovery_research",
            title="Discovery & Research",
            description="Initial research, requirement clarification, and scope alignment.",
            default_hours=6.0,
            category="Planning",
        ),
        RequirementCatalog(
            key="backend_api_endpoint",
            title="Backend API Endpoint",
            description="Design and implement a REST endpoint with validation and tests.",
            default_hours=8.0,
            category="Backend",
        ),
        RequirementCatalog(
            key="frontend_ui_view",
            title="Frontend UI View",
            description="Implement a new UI view with responsive layout and API integration.",
            default_hours=10.0,
            category="Frontend",
        ),
        RequirementCatalog(
            key="deployment_ci",
            title="Deployment & CI",
            description="Pipeline updates, containerization tweaks, environment configs.",
            default_hours=4.0,
            category="DevOps",
        ),
    ]

    for item in seed_items:
        session.add(item)


# PUBLIC_INTERFACE
async def run_bootstrap(session: AsyncSession) -> None:
    """Run bootstrap seeding to populate initial data if missing.

    This function should be called on startup after create_all.

    Args:
        session: Active AsyncSession
    """
    await _ensure_default_settings(session)
    await _ensure_catalog_seed(session)
    await session.commit()
