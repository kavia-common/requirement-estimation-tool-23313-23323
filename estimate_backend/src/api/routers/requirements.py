"""Requirement Catalog API routes.

Provides CRUD and list with search/pagination for requirement catalog items.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    PaginationMeta,
    RequirementCatalogCreate,
    RequirementCatalogList,
    RequirementCatalogRead,
    RequirementCatalogUpdate,
)
from src.db.models import RequirementCatalog
from src.db.session import get_session

router = APIRouter(prefix="/requirements", tags=["requirements"])


def _paginate_params(page: int, per_page: int) -> tuple[int, int]:
    page = max(1, page)
    per_page = max(1, min(100, per_page))
    offset = (page - 1) * per_page
    return offset, per_page


# PUBLIC_INTERFACE
@router.get(
    "/",
    response_model=RequirementCatalogList,
    summary="List catalog items",
    description="List requirement catalog items with optional search and pagination.",
)
async def list_catalog_items(
    q: Optional[str] = Query(default=None, description="Search text over key/title/description"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(default=20, ge=1, le=100, description="Page size"),
    session: AsyncSession = Depends(get_session),
):
    """Return a paginated list of catalog items matching optional filters."""
    conditions = []
    if q:
        like = f"%{q}%"
        conditions.append(
            (RequirementCatalog.key.ilike(like))
            | (RequirementCatalog.title.ilike(like))
            | (RequirementCatalog.description.ilike(like))
        )
    if category:
        conditions.append(RequirementCatalog.category == category)

    stmt = select(RequirementCatalog)
    count_stmt = select(func.count(RequirementCatalog.id))

    if conditions:
        for cond in conditions:
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

    # Order by title then id for stable ordering
    stmt = stmt.order_by(RequirementCatalog.title.asc(), RequirementCatalog.id.asc())

    # Count total
    total = (await session.execute(count_stmt)).scalar_one() or 0

    offset, limit = _paginate_params(page, per_page)
    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()

    data = [
        RequirementCatalogRead(
            id=row.id,
            key=row.key,
            title=row.title,
            description=row.description,
            default_hours=row.default_hours,
            category=row.category,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]

    pages = (total + per_page - 1) // per_page if per_page else 1
    meta = PaginationMeta(total=total, page=page, per_page=per_page, pages=pages)
    return RequirementCatalogList(data=data, meta=meta)


# PUBLIC_INTERFACE
@router.post(
    "/",
    response_model=RequirementCatalogRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create catalog item",
    description="Create a new requirement catalog item.",
)
async def create_catalog_item(
    payload: RequirementCatalogCreate, session: AsyncSession = Depends(get_session)
):
    """Create a new catalog item; 'key' should be unique."""
    # Basic uniqueness check for key
    existing = (
        await session.execute(select(RequirementCatalog).where(RequirementCatalog.key == payload.key))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Catalog item with this key already exists")

    item = RequirementCatalog(
        key=payload.key,
        title=payload.title,
        description=payload.description,
        default_hours=payload.default_hours,
        category=payload.category,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)

    return RequirementCatalogRead(
        id=item.id,
        key=item.key,
        title=item.title,
        description=item.description,
        default_hours=item.default_hours,
        category=item.category,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


# PUBLIC_INTERFACE
@router.get(
    "/{item_id}",
    response_model=RequirementCatalogRead,
    summary="Get catalog item",
    description="Retrieve a single catalog item by ID.",
)
async def get_catalog_item(item_id: int, session: AsyncSession = Depends(get_session)):
    """Fetch a catalog item by its ID."""
    item = await session.get(RequirementCatalog, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Catalog item not found")
    return RequirementCatalogRead(
        id=item.id,
        key=item.key,
        title=item.title,
        description=item.description,
        default_hours=item.default_hours,
        category=item.category,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


# PUBLIC_INTERFACE
@router.put(
    "/{item_id}",
    response_model=RequirementCatalogRead,
    summary="Update catalog item",
    description="Replace mutable fields of a catalog item by ID.",
)
async def update_catalog_item(
    item_id: int, payload: RequirementCatalogUpdate, session: AsyncSession = Depends(get_session)
):
    """Update an existing catalog item."""
    item = await session.get(RequirementCatalog, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Catalog item not found")

    if payload.key is not None and payload.key != item.key:
        # enforce uniqueness of key
        exists = (
            await session.execute(select(RequirementCatalog).where(RequirementCatalog.key == payload.key))
        ).scalar_one_or_none()
        if exists:
            raise HTTPException(status_code=409, detail="Catalog item with this key already exists")
        item.key = payload.key

    if payload.title is not None:
        item.title = payload.title
    if payload.description is not None:
        item.description = payload.description
    if payload.default_hours is not None:
        item.default_hours = payload.default_hours
    if payload.category is not None:
        item.category = payload.category

    await session.commit()
    await session.refresh(item)

    return RequirementCatalogRead(
        id=item.id,
        key=item.key,
        title=item.title,
        description=item.description,
        default_hours=item.default_hours,
        category=item.category,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


# PUBLIC_INTERFACE
@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete catalog item",
    description="Delete a catalog item by ID.",
)
async def delete_catalog_item(item_id: int, session: AsyncSession = Depends(get_session)):
    """Delete a catalog item by ID."""
    item = await session.get(RequirementCatalog, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Catalog item not found")
    await session.delete(item)
    await session.commit()
    return None
