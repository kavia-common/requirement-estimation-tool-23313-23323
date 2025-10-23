from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.models import RateCard, ComplexityDefaults
from src.schemas.reference import (
    RateCardCreate,
    RateCardRead,
    RateCardUpdate,
    ComplexityDefaultsCreate,
    ComplexityDefaultsRead,
    ComplexityDefaultsUpdate,
)

router = APIRouter(
    prefix="/reference",
    tags=["Reference Data"],
)


def _get_rate_or_404(db: Session, rate_id: int) -> RateCard:
    obj = db.get(RateCard, rate_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"RateCard {rate_id} not found")
    return obj


def _get_complexity_or_404(db: Session, defaults_id: int) -> ComplexityDefaults:
    obj = db.get(ComplexityDefaults, defaults_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"ComplexityDefaults {defaults_id} not found")
    return obj


# ---- Rate Cards ----

# PUBLIC_INTERFACE
@router.get(
    "/rates",
    response_model=List[RateCardRead],
    summary="List rate cards",
    description="Retrieve all rate cards.",
)
def list_rates(db: Session = Depends(get_db)) -> List[RateCard]:
    stmt = select(RateCard).order_by(RateCard.role.asc())
    return list(db.execute(stmt).scalars().all())


# PUBLIC_INTERFACE
@router.post(
    "/rates",
    response_model=RateCardRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create rate card",
    description="Create a new role rate card.",
)
def create_rate(payload: RateCardCreate, db: Session = Depends(get_db)) -> RateCard:
    rc = RateCard(role=payload.role, hourly_rate=payload.hourly_rate, currency=payload.currency)
    db.add(rc)
    db.commit()
    db.refresh(rc)
    return rc


# PUBLIC_INTERFACE
@router.get(
    "/rates/{rate_id}",
    response_model=RateCardRead,
    summary="Get rate card",
    description="Fetch rate card by ID.",
)
def get_rate(rate_id: int, db: Session = Depends(get_db)) -> RateCard:
    return _get_rate_or_404(db, rate_id)


# PUBLIC_INTERFACE
@router.patch(
    "/rates/{rate_id}",
    response_model=RateCardRead,
    summary="Update rate card",
    description="Update fields of a rate card.",
)
def update_rate(rate_id: int, payload: RateCardUpdate, db: Session = Depends(get_db)) -> RateCard:
    rc = _get_rate_or_404(db, rate_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rc, field, value)
    db.add(rc)
    db.commit()
    db.refresh(rc)
    return rc


# PUBLIC_INTERFACE
@router.delete(
    "/rates/{rate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete rate card",
    description="Delete a rate card by ID.",
)
def delete_rate(rate_id: int, db: Session = Depends(get_db)) -> None:
    rc = _get_rate_or_404(db, rate_id)
    db.delete(rc)
    db.commit()
    return None


# ---- Complexity Defaults ----

# PUBLIC_INTERFACE
@router.get(
    "/complexity-defaults",
    response_model=List[ComplexityDefaultsRead],
    summary="List complexity defaults",
    description="Retrieve all complexity defaults records.",
)
def list_complexity_defaults(db: Session = Depends(get_db)) -> List[ComplexityDefaults]:
    stmt = select(ComplexityDefaults).order_by(ComplexityDefaults.item_type.asc(), ComplexityDefaults.complexity.asc())
    return list(db.execute(stmt).scalars().all())


# PUBLIC_INTERFACE
@router.post(
    "/complexity-defaults",
    response_model=ComplexityDefaultsRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create complexity defaults",
    description="Create a default hours record for an item_type and complexity.",
)
def create_complexity_defaults(
    payload: ComplexityDefaultsCreate, db: Session = Depends(get_db)
) -> ComplexityDefaults:
    cd = ComplexityDefaults(
        item_type=payload.item_type,
        complexity=payload.complexity,
        default_hours=float(payload.default_hours),
    )
    db.add(cd)
    db.commit()
    db.refresh(cd)
    return cd


# PUBLIC_INTERFACE
@router.get(
    "/complexity-defaults/{defaults_id}",
    response_model=ComplexityDefaultsRead,
    summary="Get complexity defaults",
    description="Fetch a complexity defaults record by ID.",
)
def get_complexity_defaults(defaults_id: int, db: Session = Depends(get_db)) -> ComplexityDefaults:
    return _get_complexity_or_404(db, defaults_id)


# PUBLIC_INTERFACE
@router.patch(
    "/complexity-defaults/{defaults_id}",
    response_model=ComplexityDefaultsRead,
    summary="Update complexity defaults",
    description="Update fields of a complexity defaults record.",
)
def update_complexity_defaults(
    defaults_id: int, payload: ComplexityDefaultsUpdate, db: Session = Depends(get_db)
) -> ComplexityDefaults:
    cd = _get_complexity_or_404(db, defaults_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cd, field, value)
    db.add(cd)
    db.commit()
    db.refresh(cd)
    return cd


# PUBLIC_INTERFACE
@router.delete(
    "/complexity-defaults/{defaults_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete complexity defaults",
    description="Delete a complexity defaults record by ID.",
)
def delete_complexity_defaults(defaults_id: int, db: Session = Depends(get_db)) -> None:
    cd = _get_complexity_or_404(db, defaults_id)
    db.delete(cd)
    db.commit()
    return None
