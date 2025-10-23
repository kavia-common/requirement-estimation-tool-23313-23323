from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------- RateCard Schemas ----------

# PUBLIC_INTERFACE
class RateCardBase(BaseModel):
    """Shared fields for RateCard schemas."""
    role: str = Field(..., description='Role name (e.g., "developer", "qa", "pm")', min_length=1, max_length=100)
    hourly_rate: float = Field(..., description="Hourly rate for the role", ge=0.0)
    currency: str = Field("USD", description="Currency code", min_length=1, max_length=10)

    @field_validator("hourly_rate")
    @classmethod
    def validate_rate_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("hourly_rate must be non-negative")
        return v


# PUBLIC_INTERFACE
class RateCardCreate(RateCardBase):
    """Payload for creating a new RateCard."""
    pass


# PUBLIC_INTERFACE
class RateCardUpdate(BaseModel):
    """Payload for updating an existing RateCard (partial update)."""
    role: Optional[str] = Field(None, description="Role name", min_length=1, max_length=100)
    hourly_rate: Optional[float] = Field(None, description="Hourly rate", ge=0.0)
    currency: Optional[str] = Field(None, description="Currency code", min_length=1, max_length=10)

    @field_validator("hourly_rate")
    @classmethod
    def validate_rate_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("hourly_rate must be non-negative")
        return v


# PUBLIC_INTERFACE
class RateCardRead(RateCardBase):
    """Representation of a RateCard returned from the API."""
    id: int = Field(..., description="Unique identifier for the rate card")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last updated timestamp (UTC)")

    model_config = {"from_attributes": True}


# ---------- ComplexityDefaults Schemas ----------

# PUBLIC_INTERFACE
class ComplexityDefaultsBase(BaseModel):
    """Shared fields for ComplexityDefaults schemas."""
    item_type: str = Field(..., description="Item type/category", min_length=1, max_length=100)
    complexity: str = Field(..., description="Complexity level", min_length=1, max_length=50)
    default_hours: float = Field(..., description="Default hours for this item type and complexity", ge=0.0)

    @field_validator("default_hours")
    @classmethod
    def validate_hours_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("default_hours must be non-negative")
        return v


# PUBLIC_INTERFACE
class ComplexityDefaultsCreate(ComplexityDefaultsBase):
    """Payload for creating default hours for an item_type/complexity pair."""
    pass


# PUBLIC_INTERFACE
class ComplexityDefaultsUpdate(BaseModel):
    """Payload for updating default hours (partial update)."""
    item_type: Optional[str] = Field(None, description="Item type/category", min_length=1, max_length=100)
    complexity: Optional[str] = Field(None, description="Complexity level", min_length=1, max_length=50)
    default_hours: Optional[float] = Field(None, description="Default hours", ge=0.0)

    @field_validator("default_hours")
    @classmethod
    def validate_hours_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("default_hours must be non-negative")
        return v


# PUBLIC_INTERFACE
class ComplexityDefaultsRead(ComplexityDefaultsBase):
    """Representation of ComplexityDefaults returned from the API."""
    id: int = Field(..., description="Unique identifier for the default hours record")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last updated timestamp (UTC)")

    model_config = {"from_attributes": True}
