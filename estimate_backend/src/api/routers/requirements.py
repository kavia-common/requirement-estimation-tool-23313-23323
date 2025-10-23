from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.models import Requirement
from src.schemas.requirements import (
    RequirementCreate,
    RequirementRead,
    RequirementUpdate,
)

router = APIRouter(
    prefix="/requirements",
    tags=["Requirements"],
)


def _get_requirement_or_404(db: Session, requirement_id: int) -> Requirement:
    obj = db.get(Requirement, requirement_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement {requirement_id} not found",
        )
    return obj


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[RequirementRead],
    summary="List requirements",
    description="Retrieve a list of all requirements.",
)
def list_requirements(db: Session = Depends(get_db)) -> List[Requirement]:
    """List all requirements."""
    stmt = select(Requirement).order_by(Requirement.created_at.desc())
    return list(db.execute(stmt).scalars().all())


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=RequirementRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create requirement",
    description="Create a new requirement with title, description, priority and status.",
)
def create_requirement(payload: RequirementCreate, db: Session = Depends(get_db)) -> Requirement:
    """Create a new requirement."""
    req = Requirement(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        status=payload.status or "draft",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


# PUBLIC_INTERFACE
@router.get(
    "/{requirement_id}",
    response_model=RequirementRead,
    summary="Get requirement",
    description="Fetch a requirement by its ID.",
)
def get_requirement(requirement_id: int, db: Session = Depends(get_db)) -> Requirement:
    """Get a requirement by ID."""
    return _get_requirement_or_404(db, requirement_id)


# PUBLIC_INTERFACE
@router.patch(
    "/{requirement_id}",
    response_model=RequirementRead,
    summary="Update requirement",
    description="Update fields of an existing requirement.",
)
def update_requirement(
    requirement_id: int, payload: RequirementUpdate, db: Session = Depends(get_db)
) -> Requirement:
    """Update an existing requirement."""
    req = _get_requirement_or_404(db, requirement_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(req, field, value)
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


# PUBLIC_INTERFACE
@router.delete(
    "/{requirement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete requirement",
    description="Delete a requirement by its ID.",
)
def delete_requirement(requirement_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a requirement by ID."""
    req = _get_requirement_or_404(db, requirement_id)
    db.delete(req)
    db.commit()
    return None
