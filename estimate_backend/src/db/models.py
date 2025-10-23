"""Database models module.

Define SQLModel models here. This file provides base placeholders and common mixins
for future entities, and ensures SQLModel metadata is available to the app.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


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


# Example placeholder model; keep disabled by default until schema is defined.
# Uncomment and adapt when designing entities.
#
# class Requirement(TimestampMixin, SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     title: str = Field(..., description="Short title of the requirement")
#     description: Optional[str] = Field(default=None, description="Detailed description")


# PUBLIC_INTERFACE
def touch_models_metadata() -> None:
    """No-op function that references SQLModel.metadata to ensure import side effects.

    Importing this module will register all model tables in SQLModel.metadata to be
    used by init_db() for create_all/drop_all, facilitating migrations/seed workflows.
    """
    _ = SQLModel.metadata
