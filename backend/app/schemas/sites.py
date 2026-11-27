from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class SiteBase(BaseModel):
    name: str = Field(..., max_length=255, description="Site name", example="Site 7 - Central Distribution Hub")
    type: str = Field(..., max_length=100, description="Facility type", example="warehouse")
    location: Optional[str] = Field(default="Operational Zone", max_length=255, description="Physical location")
    city: Optional[str] = Field(default="London", description="City location")
    state: Optional[str] = Field(default="Greater London", description="State or province")
    country: Optional[str] = Field(default="United Kingdom", description="Country")
    pincode: Optional[str] = Field(default="E1 6AN", description="Postal/PIN code")
    user_id: Optional[uuid.UUID] = Field(default=None, description="Assigned site manager / lead user ID")
    active: bool = Field(default=True, description="Whether site is currently active")
    is_active: bool = Field(default=True, description="Whether site is currently active (mirrors active)")
    metadata_json: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata (GPS, hours)")


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    active: Optional[bool] = None
    is_active: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None


class SiteResponse(SiteBase):
    id: uuid.UUID
    site_id: Optional[uuid.UUID] = None
    serial_no: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SiteDetailResponse(SiteResponse):
    total_inspections: int = 0
    active_zones_count: int = 0
