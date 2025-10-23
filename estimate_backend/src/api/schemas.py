"""Pydantic (SQLModel) API schemas for requests and responses.

These models define the publicly documented API shapes for:
- Requirement Catalog
- Estimates and Estimate Items
- Search and pagination

Notes:
- We use SQLModel-based models for compatibility with underlying SQLModel ORM entities.
- API schemas are distinct from DB models where appropriate to control fields exposed to clients.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlmodel import SQLModel


# Shared pagination schema

class PaginationMeta(BaseModel):
    """Pagination metadata returned with list endpoints."""
    total: int = Field(..., description="Total number of records available")
    page: int = Field(..., description="Current page number (1-based)")
    per_page: int = Field(..., description="Number of records per page")
    pages: int = Field(..., description="Total number of pages")


# Requirement Catalog Schemas

class RequirementCatalogBase(SQLModel):
    """Fields common to create/update of catalog items."""
    key: str = Field(..., description="Unique key identifier for the catalog item")
    title: str = Field(..., description="Short title for the requirement template")
    description: Optional[str] = Field(default=None, description="Detailed description of the requirement")
    default_hours: float = Field(default=1.0, description="Default estimated hours for this template", ge=0.0)
    category: Optional[str] = Field(default=None, description="Optional category grouping label")


# PUBLIC_INTERFACE
class RequirementCatalogCreate(RequirementCatalogBase):
    """Payload for creating a new catalog item."""


# PUBLIC_INTERFACE
class RequirementCatalogUpdate(SQLModel):
    """Payload for partially updating an existing catalog item."""
    key: Optional[str] = Field(default=None, description="Unique key identifier")
    title: Optional[str] = Field(default=None, description="Short title")
    description: Optional[str] = Field(default=None, description="Detailed description")
    default_hours: Optional[float] = Field(default=None, description="Default hours", ge=0.0)
    category: Optional[str] = Field(default=None, description="Category label")


# PUBLIC_INTERFACE
class RequirementCatalogRead(RequirementCatalogBase):
    """Response shape for a catalog item."""
    id: int = Field(..., description="Primary key ID")
    created_at: datetime = Field(..., description="Creation timestamp UTC")
    updated_at: datetime = Field(..., description="Last update timestamp UTC")


# Estimates and Items Schemas

class EstimateItemBase(SQLModel):
    """Fields shared for estimate item create/update."""
    title: str = Field(..., description="Item title/summary")
    description: Optional[str] = Field(default=None, description="Item details")
    hours: float = Field(default=0.0, description="Estimated hours", ge=0.0)
    rate: Optional[float] = Field(default=None, description="Per-item hourly rate override")
    sequence: int = Field(default=0, description="Ordering index", ge=0)
    catalog_item_id: Optional[int] = Field(default=None, description="Optional reference to a catalog item ID")


# PUBLIC_INTERFACE
class EstimateItemCreate(EstimateItemBase):
    """Payload for creating an estimate item."""
    pass


# PUBLIC_INTERFACE
class EstimateItemUpdate(SQLModel):
    """Payload for updating an estimate item."""
    title: Optional[str] = Field(default=None, description="Item title")
    description: Optional[str] = Field(default=None, description="Item details")
    hours: Optional[float] = Field(default=None, description="Estimated hours", ge=0.0)
    rate: Optional[float] = Field(default=None, description="Hourly rate override")
    sequence: Optional[int] = Field(default=None, description="Sequence", ge=0)
    catalog_item_id: Optional[int] = Field(default=None, description="Catalog reference")


# PUBLIC_INTERFACE
class EstimateItemRead(EstimateItemBase):
    """Response for estimate item."""
    id: int = Field(..., description="Primary key ID")
    estimate_id: int = Field(..., description="Parent estimate ID")
    created_at: datetime = Field(..., description="Creation timestamp UTC")
    updated_at: datetime = Field(..., description="Last update timestamp UTC")


class EstimateBase(SQLModel):
    """Shared fields for estimates."""
    name: str = Field(..., description="Human-readable name")
    client: Optional[str] = Field(default=None, description="Client or project name")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    hourly_rate: float = Field(default=0.0, description="Hourly rate (0 means use settings default)", ge=0.0)


# PUBLIC_INTERFACE
class EstimateCreate(EstimateBase):
    """Payload for creating an estimate with optional items inline."""
    items: Optional[List[EstimateItemCreate]] = Field(default=None, description="Optional line items to create")


# PUBLIC_INTERFACE
class EstimateUpdate(SQLModel):
    """Payload for updating an estimate."""
    name: Optional[str] = Field(default=None, description="Estimate name")
    client: Optional[str] = Field(default=None, description="Client name")
    notes: Optional[str] = Field(default=None, description="Notes")
    hourly_rate: Optional[float] = Field(default=None, description="Hourly rate", ge=0.0)


# PUBLIC_INTERFACE
class EstimateRead(EstimateBase):
    """Response for an estimate with computed totals."""
    id: int = Field(..., description="Primary key ID")
    total_hours: float = Field(..., description="Computed total hours across items", ge=0.0)
    total_cost: float = Field(..., description="Computed total cost", ge=0.0)
    created_at: datetime = Field(..., description="Creation timestamp UTC")
    updated_at: datetime = Field(..., description="Last update timestamp UTC")


# PUBLIC_INTERFACE
class EstimateWithItemsRead(EstimateRead):
    """Estimate response including nested items."""
    items: List[EstimateItemRead] = Field(default_factory=list, description="Line items")


# List wrappers

# PUBLIC_INTERFACE
class RequirementCatalogList(BaseModel):
    """Paginated list of catalog items."""
    data: List[RequirementCatalogRead] = Field(..., description="Catalog items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


# PUBLIC_INTERFACE
class EstimateList(BaseModel):
    """Paginated list of estimates."""
    data: List[EstimateRead] = Field(..., description="Estimates")
    meta: PaginationMeta = Field(..., description="Pagination metadata")
