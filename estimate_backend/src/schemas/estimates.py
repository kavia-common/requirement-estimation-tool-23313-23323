from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------- EstimateItem Schemas ----------

# PUBLIC_INTERFACE
class EstimateItemBase(BaseModel):
    """Shared fields for EstimateItem schemas."""
    name: str = Field(..., description="Name of the line item", min_length=1, max_length=255)
    item_type: str = Field(
        "general",
        description='Type/category of item (e.g., "frontend", "backend", "api", "general")',
        min_length=1,
        max_length=100,
    )
    complexity: str = Field(
        "medium",
        description='Complexity of item (e.g., "low", "medium", "high")',
        min_length=1,
        max_length=50,
    )
    hours: float = Field(
        0.0,
        description="Number of hours estimated for the item",
        ge=0.0,
    )
    cost: Optional[float] = Field(
        None, description="Optional cost for the item; if not provided, cost = hours * rate"
    )

    @field_validator("hours")
    @classmethod
    def validate_hours_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("hours must be non-negative")
        return v


# PUBLIC_INTERFACE
class EstimateItemCreate(EstimateItemBase):
    """Payload for creating a new EstimateItem."""
    estimate_id: int = Field(..., description="Parent estimate ID")


# PUBLIC_INTERFACE
class EstimateItemUpdate(BaseModel):
    """Payload for updating an existing EstimateItem (partial update)."""
    name: Optional[str] = Field(None, description="Name of the line item", min_length=1, max_length=255)
    item_type: Optional[str] = Field(None, description="Type/category of item", min_length=1, max_length=100)
    complexity: Optional[str] = Field(None, description="Complexity of item", min_length=1, max_length=50)
    hours: Optional[float] = Field(None, description="Number of hours estimated for the item", ge=0.0)
    cost: Optional[float] = Field(None, description="Optional cost override for the item", ge=0.0)

    @field_validator("hours")
    @classmethod
    def validate_hours_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("hours must be non-negative")
        return v


# PUBLIC_INTERFACE
class EstimateItemRead(EstimateItemBase):
    """Representation of an EstimateItem returned from the API."""
    id: int = Field(..., description="Unique identifier for the estimate item")
    estimate_id: int = Field(..., description="Parent estimate ID")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last updated timestamp (UTC)")

    model_config = {"from_attributes": True}


# ---------- Estimate Schemas ----------

# PUBLIC_INTERFACE
class EstimateBase(BaseModel):
    """Shared fields for Estimate schemas."""
    name: str = Field(..., description="Name of the estimate", min_length=1, max_length=255)
    requirement_id: Optional[int] = Field(None, description="Associated requirement ID")
    notes: Optional[str] = Field(None, description="Optional notes for the estimate")


# PUBLIC_INTERFACE
class EstimateCreate(EstimateBase):
    """Payload for creating a new Estimate."""
    pass


# PUBLIC_INTERFACE
class EstimateUpdate(BaseModel):
    """Payload for updating an existing Estimate (partial update)."""
    name: Optional[str] = Field(None, description="Name of the estimate", min_length=1, max_length=255)
    requirement_id: Optional[int] = Field(None, description="Associated requirement ID")
    notes: Optional[str] = Field(None, description="Optional notes for the estimate")


# PUBLIC_INTERFACE
class EstimateRead(EstimateBase):
    """Representation of an Estimate returned from the API."""
    id: int = Field(..., description="Unique identifier for the estimate")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last updated timestamp (UTC)")
    items: List[EstimateItemRead] = Field(default_factory=list, description="Items belonging to this estimate")

    model_config = {"from_attributes": True}
