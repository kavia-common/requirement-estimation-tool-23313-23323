"""Estimates API routes.

Provides CRUD for estimates and estimate items, with list/search/pagination and
server-side computation of totals.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    EstimateCreate,
    EstimateItemCreate,
    EstimateItemRead,
    EstimateItemUpdate,
    EstimateList,
    EstimateRead,
    EstimateUpdate,
    EstimateWithItemsRead,
    PaginationMeta,
)
from src.db.migrations.bootstrap import DEFAULT_RATE_KEY
from src.db.models import Estimate, EstimateItem, Settings
from src.db.session import get_session

router = APIRouter(prefix="/estimates", tags=["estimates"])


def _paginate_params(page: int, per_page: int) -> tuple[int, int]:
    page = max(1, page)
    per_page = max(1, min(100, per_page))
    offset = (page - 1) * per_page
    return offset, per_page


async def _get_default_rate(session: AsyncSession) -> float:
    """Fetch default hourly rate from settings."""
    result = await session.execute(select(Settings).where(Settings.key == DEFAULT_RATE_KEY))
    s = result.scalar_one_or_none()
    if not s:
        return 0.0
    try:
        return float(s.value)
    except Exception:
        return 0.0


def _compute_item_cost(hours: float, rate: float) -> float:
    return float(round(hours * rate, 2))


async def _compute_totals(session: AsyncSession, estimate: Estimate) -> None:
    """Recalculate and persist total_hours and total_cost."""
    # Fetch items fresh to ensure alignment
    items = (await session.execute(select(EstimateItem).where(EstimateItem.estimate_id == estimate.id))).scalars().all()
    total_hours = sum(i.hours or 0.0 for i in items)

    # rate resolution: item.rate -> estimate.hourly_rate -> default rate
    default_rate = await _get_default_rate(session)
    total_cost = 0.0
    for i in items:
        rate = i.rate if i.rate is not None else (estimate.hourly_rate if estimate.hourly_rate else default_rate)
        total_cost += _compute_item_cost(i.hours or 0.0, rate or 0.0)

    estimate.total_hours = float(round(total_hours, 2))
    estimate.total_cost = float(round(total_cost, 2))


# PUBLIC_INTERFACE
@router.get(
    "/",
    response_model=EstimateList,
    summary="List estimates",
    description="List estimates with optional search by name/client and pagination.",
)
async def list_estimates(
    q: Optional[str] = Query(default=None, description="Search text over name/client"),
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(default=20, ge=1, le=100, description="Page size"),
    session: AsyncSession = Depends(get_session),
):
    """Return a paginated list of estimates."""
    stmt = select(Estimate)
    count_stmt = select(func.count(Estimate.id))

    if q:
        like = f"%{q}%"
        cond = (Estimate.name.ilike(like)) | (Estimate.client.ilike(like))
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    stmt = stmt.order_by(Estimate.updated_at.desc(), Estimate.id.desc())

    total = (await session.execute(count_stmt)).scalar_one() or 0
    offset, limit = _paginate_params(page, per_page)
    rows = (await session.execute(stmt.offset(offset).limit(limit))).scalars().all()

    data = [
        EstimateRead(
            id=row.id,
            name=row.name,
            client=row.client,
            notes=row.notes,
            hourly_rate=row.hourly_rate,
            total_hours=row.total_hours,
            total_cost=row.total_cost,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]
    pages = (total + per_page - 1) // per_page if per_page else 1
    meta = PaginationMeta(total=total, page=page, per_page=per_page, pages=pages)
    return EstimateList(data=data, meta=meta)


# PUBLIC_INTERFACE
@router.post(
    "/",
    response_model=EstimateWithItemsRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create estimate",
    description="Create an estimate with optional items.",
)
async def create_estimate(payload: EstimateCreate, session: AsyncSession = Depends(get_session)):
    """Create an estimate and optional items; compute totals."""
    est = Estimate(
        name=payload.name,
        client=payload.client,
        notes=payload.notes,
        hourly_rate=payload.hourly_rate or 0.0,
    )
    session.add(est)
    await session.flush()  # ensure est.id

    if payload.items:
        for idx, it in enumerate(payload.items):
            item = EstimateItem(
                estimate_id=est.id,
                title=it.title,
                description=it.description,
                hours=it.hours or 0.0,
                rate=it.rate,
                sequence=it.sequence if it.sequence is not None else idx,
                catalog_item_id=it.catalog_item_id,
            )
            session.add(item)

    await _compute_totals(session, est)
    await session.commit()
    await session.refresh(est)

    items = (
        await session.execute(select(EstimateItem).where(EstimateItem.estimate_id == est.id).order_by(EstimateItem.sequence.asc(), EstimateItem.id.asc()))
    ).scalars().all()

    return EstimateWithItemsRead(
        id=est.id,
        name=est.name,
        client=est.client,
        notes=est.notes,
        hourly_rate=est.hourly_rate,
        total_hours=est.total_hours,
        total_cost=est.total_cost,
        created_at=est.created_at,
        updated_at=est.updated_at,
        items=[
            EstimateItemRead(
                id=i.id,
                estimate_id=i.estimate_id,
                title=i.title,
                description=i.description,
                hours=i.hours,
                rate=i.rate,
                sequence=i.sequence,
                catalog_item_id=i.catalog_item_id,
                created_at=i.created_at,
                updated_at=i.updated_at,
            )
            for i in items
        ],
    )


# PUBLIC_INTERFACE
@router.get(
    "/{estimate_id}",
    response_model=EstimateWithItemsRead,
    summary="Get estimate",
    description="Retrieve a single estimate by ID with items.",
)
async def get_estimate(estimate_id: int, session: AsyncSession = Depends(get_session)):
    """Fetch an estimate and its items."""
    est = await session.get(Estimate, estimate_id)
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")

    items = (
        await session.execute(select(EstimateItem).where(EstimateItem.estimate_id == estimate_id).order_by(EstimateItem.sequence.asc(), EstimateItem.id.asc()))
    ).scalars().all()

    return EstimateWithItemsRead(
        id=est.id,
        name=est.name,
        client=est.client,
        notes=est.notes,
        hourly_rate=est.hourly_rate,
        total_hours=est.total_hours,
        total_cost=est.total_cost,
        created_at=est.created_at,
        updated_at=est.updated_at,
        items=[
            EstimateItemRead(
                id=i.id,
                estimate_id=i.estimate_id,
                title=i.title,
                description=i.description,
                hours=i.hours,
                rate=i.rate,
                sequence=i.sequence,
                catalog_item_id=i.catalog_item_id,
                created_at=i.created_at,
                updated_at=i.updated_at,
            )
            for i in items
        ],
    )


# PUBLIC_INTERFACE
@router.put(
    "/{estimate_id}",
    response_model=EstimateRead,
    summary="Update estimate",
    description="Update fields of an existing estimate and recompute totals.",
)
async def update_estimate(
    estimate_id: int, payload: EstimateUpdate, session: AsyncSession = Depends(get_session)
):
    """Update estimate and recompute totals."""
    est = await session.get(Estimate, estimate_id)
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")

    if payload.name is not None:
        est.name = payload.name
    if payload.client is not None:
        est.client = payload.client
    if payload.notes is not None:
        est.notes = payload.notes
    if payload.hourly_rate is not None:
        est.hourly_rate = payload.hourly_rate

    await _compute_totals(session, est)
    await session.commit()
    await session.refresh(est)

    return EstimateRead(
        id=est.id,
        name=est.name,
        client=est.client,
        notes=est.notes,
        hourly_rate=est.hourly_rate,
        total_hours=est.total_hours,
        total_cost=est.total_cost,
        created_at=est.created_at,
        updated_at=est.updated_at,
    )


# PUBLIC_INTERFACE
@router.delete(
    "/{estimate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete estimate",
    description="Delete an estimate and its items.",
)
async def delete_estimate(estimate_id: int, session: AsyncSession = Depends(get_session)):
    """Delete an estimate by ID including its items."""
    est = await session.get(Estimate, estimate_id)
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")

    # Delete items first due to FK
    items = (
        await session.execute(select(EstimateItem).where(EstimateItem.estimate_id == estimate_id))
    ).scalars().all()
    for i in items:
        await session.delete(i)

    await session.delete(est)
    await session.commit()
    return None


# ----- Nested Items Management ----- #

# PUBLIC_INTERFACE
@router.post(
    "/{estimate_id}/items",
    response_model=EstimateItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add item to estimate",
    description="Create a new estimate item under a given estimate and recompute totals.",
)
async def add_item(
    estimate_id: int,
    payload: EstimateItemCreate,
    session: AsyncSession = Depends(get_session),
):
    """Append a new item to an estimate and recompute totals."""
    est = await session.get(Estimate, estimate_id)
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")

    # Determine next sequence if not provided
    if payload.sequence is None:
        max_seq = (
            await session.execute(
                select(func.max(EstimateItem.sequence)).where(EstimateItem.estimate_id == estimate_id)
            )
        ).scalar_one()
        next_seq = (max_seq or 0) + 1
    else:
        next_seq = payload.sequence

    item = EstimateItem(
        estimate_id=estimate_id,
        title=payload.title,
        description=payload.description,
        hours=payload.hours or 0.0,
        rate=payload.rate,
        sequence=next_seq,
        catalog_item_id=payload.catalog_item_id,
    )
    session.add(item)

    await session.flush()
    await _compute_totals(session, est)
    await session.commit()
    await session.refresh(item)

    return EstimateItemRead(
        id=item.id,
        estimate_id=item.estimate_id,
        title=item.title,
        description=item.description,
        hours=item.hours,
        rate=item.rate,
        sequence=item.sequence,
        catalog_item_id=item.catalog_item_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


# PUBLIC_INTERFACE
@router.put(
    "/{estimate_id}/items/{item_id}",
    response_model=EstimateItemRead,
    summary="Update estimate item",
    description="Update fields of an estimate item and recompute totals.",
)
async def update_item(
    estimate_id: int,
    item_id: int,
    payload: EstimateItemUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update an existing item under an estimate."""
    est = await session.get(Estimate, estimate_id)
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")

    item = await session.get(EstimateItem, item_id)
    if not item or item.estimate_id != estimate_id:
        raise HTTPException(status_code=404, detail="Item not found")

    if payload.title is not None:
        item.title = payload.title
    if payload.description is not None:
        item.description = payload.description
    if payload.hours is not None:
        item.hours = payload.hours
    if payload.rate is not None:
        item.rate = payload.rate
    if payload.sequence is not None:
        item.sequence = payload.sequence
    if payload.catalog_item_id is not None:
        item.catalog_item_id = payload.catalog_item_id

    await _compute_totals(session, est)
    await session.commit()
    await session.refresh(item)

    return EstimateItemRead(
        id=item.id,
        estimate_id=item.estimate_id,
        title=item.title,
        description=item.description,
        hours=item.hours,
        rate=item.rate,
        sequence=item.sequence,
        catalog_item_id=item.catalog_item_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


# PUBLIC_INTERFACE
@router.delete(
    "/{estimate_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete estimate item",
    description="Remove an estimate item and recompute totals.",
)
async def delete_item(
    estimate_id: int,
    item_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete an item under an estimate and recompute totals."""
    est = await session.get(Estimate, estimate_id)
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")

    item = await session.get(EstimateItem, item_id)
    if not item or item.estimate_id != estimate_id:
        raise HTTPException(status_code=404, detail="Item not found")

    await session.delete(item)
    await _compute_totals(session, est)
    await session.commit()
    return None
