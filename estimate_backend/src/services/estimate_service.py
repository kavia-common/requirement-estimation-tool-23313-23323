from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.db.models import ComplexityDefaults, Estimate, EstimateItem, RateCard


@dataclass
class EstimateTotals:
    """Container for totals and rollups."""
    estimate_id: int
    currency: str
    total_hours: float
    total_cost: float
    by_role: Dict[str, Dict[str, float]]  # role -> {"hours": float, "cost": float}
    items: List[Dict[str, float]]  # per-item summary: {"id", "hours", "rate", "cost"}


def _get_default_hours(db: Session, item_type: str, complexity: str) -> Optional[float]:
    """Fetch default hours for a given item_type and complexity from ComplexityDefaults."""
    stmt: Select = select(ComplexityDefaults.default_hours).where(
        (ComplexityDefaults.item_type == item_type) & (ComplexityDefaults.complexity == complexity)
    )
    res = db.execute(stmt).scalar_one_or_none()
    return float(res) if res is not None else None


def _get_rate_for_role(db: Session, role: str) -> Optional[Tuple[float, str]]:
    """Fetch hourly rate and currency for a given role from RateCard."""
    stmt: Select = select(RateCard.hourly_rate, RateCard.currency).where(RateCard.role == role)
    row = db.execute(stmt).first()
    if not row:
        return None
    rate_dec, currency = row
    # RateCard.hourly_rate is Numeric; convert to float for interoperability here
    return float(Decimal(rate_dec)), currency  # type: ignore[arg-type]


def _pick_role_for_item(item: EstimateItem) -> str:
    """Derive a default role for an EstimateItem based on its item_type.

    This is a simple heuristic and can be expanded later or driven by a mapping table.
    """
    mapping = {
        "frontend": "developer",
        "backend": "developer",
        "api": "developer",
        "general": "developer",
        "design": "designer",
        "qa": "qa",
        "pm": "pm",
    }
    return mapping.get(item.item_type.lower(), "developer")


# PUBLIC_INTERFACE
def calculate_totals(db: Session, estimate_id: int) -> EstimateTotals:
    """Compute totals for an estimate, including per-item cost and a summary by role.

    Args:
        db: SQLAlchemy ORM Session.
        estimate_id: The ID of the Estimate to compute totals for.

    Returns:
        EstimateTotals: aggregate hours and cost with per-role breakdown.

    Behavior:
        - If an item has hours <= 0, attempts to fill from ComplexityDefaults based on
          (item_type, complexity). If still <= 0, the item contributes 0.
        - Role is inferred based on item_type via a simple mapping. Rate is obtained from RateCard.
          If no rate for a role is found, rate=0 with inherited/first available currency.
        - Item cost = hours * rate, rounded to two decimals for presentation.
        - Totals include:
            * total_hours: sum of hours across items
            * total_cost: sum of costs across items
            * by_role: aggregate hours and costs grouped by role
    """
    # Ensure estimate exists and load items
    estimate: Optional[Estimate] = db.get(Estimate, estimate_id)
    if not estimate:
        raise ValueError(f"Estimate {estimate_id} not found")

    items_stmt: Select = select(EstimateItem).where(EstimateItem.estimate_id == estimate_id)
    items: List[EstimateItem] = list(db.execute(items_stmt).scalars().all())

    by_role: Dict[str, Dict[str, float]] = defaultdict(lambda: {"hours": 0.0, "cost": 0.0})
    items_summary: List[Dict[str, float]] = []
    total_hours = 0.0
    total_cost = 0.0

    # Default currency if none found in the first rate lookup
    currency: Optional[str] = None

    for item in items:
        hours = float(item.hours or 0.0)
        if hours <= 0.0:
            default_hours = _get_default_hours(db, item.item_type, item.complexity)
            if default_hours is not None:
                hours = float(default_hours)

        role = _pick_role_for_item(item)
        rate_info = _get_rate_for_role(db, role)
        if rate_info:
            rate, rate_currency = rate_info
            currency = currency or rate_currency
        else:
            rate = 0.0
            # Leave currency as-is; will set a fallback below if still None

        cost = round(hours * rate, 2)

        # Aggregate
        by_role[role]["hours"] += hours
        by_role[role]["cost"] += cost
        total_hours += hours
        total_cost += cost

        items_summary.append(
            {
                "id": float(item.id),  # keeping values float for consistent JSON typing if needed
                "hours": hours,
                "rate": rate,
                "cost": cost,
            }
        )

    if currency is None:
        # Fallback: try the first rate card currency available, else default to USD
        rc_currency = db.execute(select(RateCard.currency).limit(1)).scalar_one_or_none()
        currency = rc_currency or "USD"

    # Round totals for consistent presentation
    total_hours = round(total_hours, 2)
    total_cost = round(total_cost, 2)
    # Also round per-role aggregates
    for r, agg in by_role.items():
        agg["hours"] = round(agg["hours"], 2)
        agg["cost"] = round(agg["cost"], 2)

    return EstimateTotals(
        estimate_id=estimate_id,
        currency=currency,
        total_hours=total_hours,
        total_cost=total_cost,
        by_role=dict(by_role),
        items=items_summary,
    )
