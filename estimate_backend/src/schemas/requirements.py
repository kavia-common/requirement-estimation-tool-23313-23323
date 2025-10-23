from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# PUBLIC_INTERFACE
class RequirementBase(BaseModel):
    """Shared fields for Requirement schemas."""
    title: str = Field(..., description="Title of the requirement", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Detailed description of the requirement")
    priority: Optional[str] = Field(None, description="Priority level e.g., Low, Medium, High")
    status: Optional[str] = Field("draft", description="Status of the requirement")


# PUBLIC_INTERFACE
class RequirementCreate(RequirementBase):
    """Payload for creating a new Requirement."""
    pass


# PUBLIC_INTERFACE
class RequirementUpdate(BaseModel):
    """Payload for updating an existing Requirement (partial update)."""
    title: Optional[str] = Field(None, description="Title of the requirement", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Detailed description of the requirement")
    priority: Optional[str] = Field(None, description="Priority level e.g., Low, Medium, High")
    status: Optional[str] = Field(None, description="Status of the requirement")


# PUBLIC_INTERFACE
class RequirementRead(RequirementBase):
    """Representation of a Requirement returned from the API."""
    id: int = Field(..., description="Unique identifier for the requirement")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last updated timestamp (UTC)")

    model_config = {
        "from_attributes": True  # Pydantic v2: allow construction from ORM instances
    }
