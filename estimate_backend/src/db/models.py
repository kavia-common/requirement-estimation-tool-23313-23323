"""Database models module.

Define SQLModel models for the application schema and provide metadata exposure
for engine initialization. Uses async-friendly SQLModel/SQLAlchemy 2.x.

Models:
- RequirementCatalog: Catalog items that can be used to build estimates.
- Estimate: A parent record representing a single estimate.
- EstimateItem: Line items belonging to an estimate, referencing a catalog item (optional).
- Settings: Key/value configuration store (e.g., default hourly rate).

Notes:
- All timestamps are stored in UTC.
- Monetary values are represented as float for simplicity; consider Decimal for finance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class TimestampMixin(SQLModel):
    """Common created_at/updated_at fields. Use in concrete models via multiple inheritance."""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp in UTC.",
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp in UTC.",
        nullable=False,
    )


class RequirementCatalogBase(SQLModel):
    """Shared fields for requirement catalog."""

    key: str = Field(..., description="Unique key identifier for the catalog item", index=True)
    title: str = Field(..., description="Short title for the requirement template")
    description: Optional[str] = Field(default=None, description="Detailed description of the requirement")
    default_hours: float = Field(
        default=1.0,
        description="Default estimated hours for this requirement template",
        ge=0.0,
    )
    category: Optional[str] = Field(default=None, description="Optional category grouping label")


class RequirementCatalog(TimestampMixin, RequirementCatalogBase, table=True):
    """Requirement catalog table."""

    id: Optional[int] = Field(default=None, primary_key=True)

    # Backref from EstimateItem
    estimate_items: List["EstimateItem"] = Relationship(back_populates="catalog_item")


class EstimateBase(SQLModel):
    """Shared fields for estimates."""

    name: str = Field(..., description="Human-friendly name of the estimate")
    client: Optional[str] = Field(default=None, description="Client or project name")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    hourly_rate: float = Field(
        default=0.0,
        description="Hourly rate applied for this estimate; if 0, use settings default",
        ge=0.0,
    )


class Estimate(TimestampMixin, EstimateBase, table=True):
    """Estimate parent entity."""

    id: Optional[int] = Field(default=None, primary_key=True)
    total_hours: float = Field(default=0.0, description="Total hours across items", ge=0.0)
    total_cost: float = Field(default=0.0, description="Computed total cost", ge=0.0)

    # Relationship to items
    items: List["EstimateItem"] = Relationship(back_populates="estimate")


class EstimateItemBase(SQLModel):
    """Shared fields for estimate items."""

    title: str = Field(..., description="Item title/summary")
    description: Optional[str] = Field(default=None, description="Item details")
    hours: float = Field(default=0.0, description="Estimated hours for this item", ge=0.0)
    rate: Optional[float] = Field(default=None, description="Optional override hourly rate; if None, use estimate/hourly rate")
    sequence: int = Field(default=0, description="Ordering index", ge=0)


class EstimateItem(TimestampMixin, EstimateItemBase, table=True):
    """Estimate line item."""

    id: Optional[int] = Field(default=None, primary_key=True)

    estimate_id: int = Field(foreign_key="estimate.id", index=True, nullable=False)
    catalog_item_id: Optional[int] = Field(default=None, foreign_key="requirementcatalog.id", index=True)

    # Relationships
    estimate: Estimate = Relationship(back_populates="items")
    catalog_item: Optional[RequirementCatalog] = Relationship(back_populates="estimate_items")


class SettingsBase(SQLModel):
    """Shared fields for app settings."""

    key: str = Field(..., description="Settings key", index=True)
    value: str = Field(..., description="Settings value as string")
    description: Optional[str] = Field(default=None, description="Description/help text")


class Settings(TimestampMixin, SettingsBase, table=True):
    """Simple key-value settings store."""

    id: Optional[int] = Field(default=None, primary_key=True)
    # unique key constraint handled via index and code-level checks


# PUBLIC_INTERFACE
def touch_models_metadata() -> None:
    """No-op that references SQLModel.metadata to ensure model registration.

    Importing this module registers all models' tables to SQLModel.metadata which is
    then used during init_db() for create_all().
    """
    _ = SQLModel.metadata
