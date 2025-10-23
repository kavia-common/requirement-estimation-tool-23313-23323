"""Calculation service for estimates and items.

Provides functions to:
- compute line hours using quantity, base_hours, complexity_factor, and risk_factor
- fetch hourly rate from settings with environment fallback
- compute and persist totals for an estimate

Environment variables:
- HOURLY_RATE: fallback hourly rate used if no settings value is present
"""

from __future__ import annotations

import os

from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.migrations.bootstrap import DEFAULT_RATE_KEY
from src.db.models import Estimate, EstimateItem, Settings


# PUBLIC_INTERFACE
def compute_line_hours(
    quantity: float,
    base_hours: float,
    complexity_factor: float,
    risk_factor: float,
) -> float:
    """Compute line hours as quantity * base_hours * complexity_factor * risk_factor.

    Args:
        quantity: Number of units (e.g., screens, endpoints).
        base_hours: Base hours per unit.
        complexity_factor: Complexity multiplier.
        risk_factor: Risk multiplier.

    Returns:
        The computed hours as a float rounded to 2 decimals.
    """
    q = float(quantity or 0.0)
    b = float(base_hours or 0.0)
    c = float(complexity_factor or 1.0)
    r = float(risk_factor or 1.0)
    return float(round(q * b * c * r, 2))


async def _get_env_hourly_rate() -> float:
    """Get hourly rate from HOURLY_RATE environment variable if available."""
    raw = os.getenv("HOURLY_RATE")
    if not raw:
        return 0.0
    try:
        return float(raw)
    except Exception:
        return 0.0


# PUBLIC_INTERFACE
async def get_effective_default_rate(session: AsyncSession) -> float:
    """Return the default hourly rate from settings, falling back to env HOURLY_RATE.

    Args:
        session: Active AsyncSession used to query settings.

    Returns:
        Default hourly rate as float (>= 0.0).
    """
    # Try settings first
    result = await session.execute(select(Settings).where(Settings.key == DEFAULT_RATE_KEY))
    s: Optional[Settings] = result.scalar_one_or_none()
    if s:
        try:
            rate = float(s.value)
            if rate >= 0.0:
                return rate
        except Exception:
            ...

    # Fallback to env
    env_rate = await _get_env_hourly_rate()
    return env_rate if env_rate >= 0.0 else 0.0


def _resolve_item_rate(item: EstimateItem, estimate: Estimate, default_rate: float) -> float:
    """Resolve the rate for an item: item.rate -> estimate.hourly_rate -> default."""
    if item.rate is not None:
        return float(item.rate)
    if estimate.hourly_rate:
        return float(estimate.hourly_rate)
    return float(default_rate or 0.0)


# PUBLIC_INTERFACE
async def recompute_and_persist_totals(session: AsyncSession, estimate: Estimate) -> None:
    """Recalculate estimate totals (hours and cost) and persist to the DB.

    Steps:
    1) Load items for the estimate.
    2) Resolve default hourly rate from settings or environment.
    3) Sum item hours, and compute item cost using resolved rate.
    4) Persist totals on the estimate.

    Args:
        session: Async database session.
        estimate: The Estimate entity to recompute.
    """
    items: Iterable[EstimateItem] = (
        await session.execute(select(EstimateItem).where(EstimateItem.estimate_id == estimate.id))
    ).scalars().all()

    total_hours = sum(float(i.hours or 0.0) for i in items)
    default_rate = await get_effective_default_rate(session)

    total_cost = 0.0
    for i in items:
        rate = _resolve_item_rate(i, estimate, default_rate)
        total_cost += float((i.hours or 0.0) * (rate or 0.0))

    estimate.total_hours = float(round(total_hours, 2))
    estimate.total_cost = float(round(total_cost, 2))
