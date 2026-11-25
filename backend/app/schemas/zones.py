from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ZoneConfigBase(BaseModel):
    site_id: uuid.UUID = Field(..., description="Site ID")
    camera_id: Optional[str] = Field(default=None, description="Optional camera ID")
    name: str = Field(..., max_length=150, description="Zone name", example="Emergency Exit Clear Zone")
    zone_type: str = Field(default="polygon", description="polygon | counting_line")
    coordinates: List[Any] = Field(..., description="Array of points [[x, y], ...]")
    applicable_classes: List[str] = Field(..., description="Classes evaluated in this zone", example=["pallet", "spill"])
    rules_config: Optional[Dict[str, Any]] = Field(default=None, description="Zone threshold settings")
    is_active: bool = Field(default=True, description="Active status")


class ZoneConfigCreate(ZoneConfigBase):
    pass


class ZoneConfigResponse(ZoneConfigBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SiteZonesSummary(BaseModel):
    site_id: uuid.UUID
    zones: List[ZoneConfigResponse] = Field(default_factory=list)
    lines: List[ZoneConfigResponse] = Field(default_factory=list)
