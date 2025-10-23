"""
SQLAlchemy ORM models for the estimation backend.

Defines:
- Requirement: A single requirement to be estimated.
- Estimate: A collection of estimated items for a requirement or project.
- EstimateItem: An individual line item in an estimate, with complexity and hours.
- RateCard: Defines role-based hourly rates and currency.
- ComplexityDefaults: Default hours per complexity category for a given item type.

Provides:
- Base: declarative base for all models (importable for metadata.create_all).
- metadata: alias to Base.metadata for convenient engine binding elsewhere.

Note: Tables are named explicitly to remain stable across migrations.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


# Expose metadata for engine.bind create_all usage
metadata = Base.metadata


class TimestampMixin:
    """Adds created_at and updated_at timestamps to inheriting models."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Requirement(TimestampMixin, Base):
    """Represents a functional or technical requirement to be estimated."""
    __tablename__ = "requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., Low/Medium/High
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)

    # Relationships
    estimates: Mapped[list["Estimate"]] = relationship(
        back_populates="requirement", cascade="all, delete-orphan"
    )


class Estimate(TimestampMixin, Base):
    """Represents an estimate, typically for a single requirement or group."""
    __tablename__ = "estimates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    requirement_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    requirement: Mapped[Optional[Requirement]] = relationship(back_populates="estimates")
    items: Mapped[list["EstimateItem"]] = relationship(
        back_populates="estimate", cascade="all, delete-orphan"
    )


class EstimateItem(TimestampMixin, Base):
    """A line item in an estimate, representing a task or component."""
    __tablename__ = "estimate_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    estimate_id: Mapped[int] = mapped_column(
        ForeignKey("estimates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    item_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="general"
    )  # e.g., "frontend", "backend", "api"
    complexity: Mapped[str] = mapped_column(
        String(50), nullable=False, default="medium"
    )  # e.g., "low", "medium", "high"
    hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Optional: computed or entered cost; total would be hours * rate; stored if needed
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    estimate: Mapped[Estimate] = relationship(back_populates="items")


class RateCard(TimestampMixin, Base):
    """Defines billable rates per role."""
    __tablename__ = "rate_cards"
    __table_args__ = (
        UniqueConstraint("role", name="uq_rate_cards_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "developer", "qa", "pm"
    hourly_rate: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False
    )  # store as numeric for predictable arithmetic
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")


class ComplexityDefaults(TimestampMixin, Base):
    """Default hours for item_type + complexity pairs (used to prefill EstimateItem hours)."""
    __tablename__ = "complexity_defaults"
    __table_args__ = (
        UniqueConstraint("item_type", "complexity", name="uq_complexity_defaults_item_type_complexity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_type: Mapped[str] = mapped_column(String(100), nullable=False)
    complexity: Mapped[str] = mapped_column(String(50), nullable=False)  # low, medium, high, etc.
    default_hours: Mapped[float] = mapped_column(Float, nullable=False)
