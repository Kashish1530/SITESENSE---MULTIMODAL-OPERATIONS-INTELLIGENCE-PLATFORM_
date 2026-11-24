from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class SiteBase(BaseModel):
    name: str = Field(..., max_length=255, description="Site name", example="Site 7 - Central Distribution Hub")
    type: str = Field(..., max_length=100, description="Facility type", example="warehouse")
    location: str = Field(..., max_length=255, description="Physical location", example="Zone 4 Industrial Park, London")
    active: bool = Field(default=True, description="Whether site is currently active")
    metadata_json: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata (GPS, hours)")


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    location: Optional[str] = None
    active: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None


class SiteResponse(SiteBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SiteDetailResponse(SiteResponse):
    total_inspections: int = 0
    active_zones_count: int = 0
