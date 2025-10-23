from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.models import Estimate, EstimateItem
from src.schemas.estimates import (
    EstimateCreate,
    EstimateItemCreate,
    EstimateItemRead,
    EstimateItemUpdate,
    EstimateRead,
    EstimateUpdate,
)
from src.services import calculate_totals, EstimateTotals

router = APIRouter(
    prefix="/estimates",
    tags=["Estimates"],
)


def _get_estimate_or_404(db: Session, estimate_id: int) -> Estimate:
    obj = db.get(Estimate, estimate_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate {estimate_id} not found",
        )
    return obj


def _get_item_or_404(db: Session, item_id: int) -> EstimateItem:
    obj = db.get(EstimateItem, item_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate item {item_id} not found",
        )
    return obj


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[EstimateRead],
    summary="List estimates",
    description="Retrieve all estimates with nested items.",
)
def list_estimates(db: Session = Depends(get_db)) -> List[Estimate]:
    """List all estimates, including items."""
    stmt = select(Estimate).order_by(Estimate.created_at.desc())
    return list(db.execute(stmt).scalars().unique().all())


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=EstimateRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create estimate",
    description="Create a new estimate. Optionally associate to a requirement.",
)
def create_estimate(payload: EstimateCreate, db: Session = Depends(get_db)) -> Estimate:
    """Create a new estimate."""
    est = Estimate(
        name=payload.name,
        requirement_id=payload.requirement_id,
        notes=payload.notes,
    )
    db.add(est)
    db.commit()
    db.refresh(est)
    return est


# PUBLIC_INTERFACE
@router.get(
    "/{estimate_id}",
    response_model=EstimateRead,
    summary="Get estimate",
    description="Fetch an estimate by its ID with nested items.",
)
def get_estimate(estimate_id: int, db: Session = Depends(get_db)) -> Estimate:
    """Get estimate by ID."""
    return _get_estimate_or_404(db, estimate_id)


# PUBLIC_INTERFACE
@router.patch(
    "/{estimate_id}",
    response_model=EstimateRead,
    summary="Update estimate",
    description="Update fields of an existing estimate.",
)
def update_estimate(
    estimate_id: int, payload: EstimateUpdate, db: Session = Depends(get_db)
) -> Estimate:
    """Update an estimate."""
    est = _get_estimate_or_404(db, estimate_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(est, field, value)
    db.add(est)
    db.commit()
    db.refresh(est)
    return est


# PUBLIC_INTERFACE
@router.delete(
    "/{estimate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete estimate",
    description="Delete an estimate and its items.",
)
def delete_estimate(estimate_id: int, db: Session = Depends(get_db)) -> None:
    """Delete an estimate (cascade deletes items)."""
    est = _get_estimate_or_404(db, estimate_id)
    db.delete(est)
    db.commit()
    return None


# ---------- Items Sub-Resources ----------

# PUBLIC_INTERFACE
@router.get(
    "/{estimate_id}/items",
    response_model=List[EstimateItemRead],
    summary="List estimate items",
    description="List all items belonging to an estimate.",
)
def list_items(estimate_id: int, db: Session = Depends(get_db)) -> List[EstimateItem]:
    """List items for an estimate."""
    _ = _get_estimate_or_404(db, estimate_id)
    stmt = select(EstimateItem).where(EstimateItem.estimate_id == estimate_id).order_by(
        EstimateItem.created_at.asc()
    )
    return list(db.execute(stmt).scalars().all())


# PUBLIC_INTERFACE
@router.post(
    "/{estimate_id}/items",
    response_model=EstimateItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create estimate item",
    description="Create a new estimate item under the given estimate.",
)
def create_item(
    estimate_id: int, payload: EstimateItemCreate, db: Session = Depends(get_db)
) -> EstimateItem:
    """Create new item under an estimate."""
    _ = _get_estimate_or_404(db, estimate_id)
    if payload.estimate_id != estimate_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="estimate_id in body must match URL estimate_id",
        )
    item = EstimateItem(
        estimate_id=estimate_id,
        name=payload.name,
        item_type=payload.item_type,
        complexity=payload.complexity,
        hours=float(payload.hours or 0.0),
        cost=payload.cost,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# PUBLIC_INTERFACE
@router.get(
    "/items/{item_id}",
    response_model=EstimateItemRead,
    summary="Get estimate item",
    description="Fetch a single estimate item by its ID.",
)
def get_item(item_id: int, db: Session = Depends(get_db)) -> EstimateItem:
    """Get a single item by ID."""
    return _get_item_or_404(db, item_id)


# PUBLIC_INTERFACE
@router.patch(
    "/items/{item_id}",
    response_model=EstimateItemRead,
    summary="Update estimate item",
    description="Update fields of an estimate item.",
)
def update_item(item_id: int, payload: EstimateItemUpdate, db: Session = Depends(get_db)) -> EstimateItem:
    """Update an estimate item."""
    item = _get_item_or_404(db, item_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# PUBLIC_INTERFACE
@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete estimate item",
    description="Delete an estimate item by its ID.",
)
def delete_item(item_id: int, db: Session = Depends(get_db)) -> None:
    """Delete an estimate item."""
    item = _get_item_or_404(db, item_id)
    db.delete(item)
    db.commit()
    return None


# PUBLIC_INTERFACE
@router.post(
    "/{estimate_id}/recalc",
    response_model=dict,
    summary="Recalculate totals",
    description="Recalculate totals and per-role breakdown for the estimate.",
)
def recalc_totals(estimate_id: int, db: Session = Depends(get_db)) -> Dict:
    """Recalculate totals using the service layer."""
    _ = _get_estimate_or_404(db, estimate_id)
    totals: EstimateTotals = calculate_totals(db, estimate_id)
    # Return as JSON-compatible dict
    return {
        "estimate_id": totals.estimate_id,
        "currency": totals.currency,
        "total_hours": totals.total_hours,
        "total_cost": totals.total_cost,
        "by_role": totals.by_role,
        "items": totals.items,
    }
