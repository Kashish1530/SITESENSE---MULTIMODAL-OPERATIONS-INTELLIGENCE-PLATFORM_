from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class DetectionItem(BaseModel):
    id: uuid.UUID
    media_id: uuid.UUID
    class_name: str
    bbox: List[float] = Field(..., description="[x1, y1, x2, y2] absolute pixel coordinates")
    confidence: float
    zone: Optional[str] = None
    frame_no: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ExtractionItem(BaseModel):
    id: uuid.UUID
    media_id: uuid.UUID
    field_name: str
    value: str
    confidence: float
    status: Optional[str] = "pending_review"
    reviewed_by: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)


class MediaItem(BaseModel):
    id: uuid.UUID
    inspection_id: uuid.UUID
    type: str
    path: str
    filename: Optional[str] = None
    is_annotated: bool = False
    annotated_path: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FindingItem(BaseModel):
    id: uuid.UUID
    inspection_id: uuid.UUID
    rule_id: uuid.UUID
    rule_name: Optional[str] = None
    status: str = Field(..., description="pass | fail | review")
    evidence_ids: List[str] = Field(default_factory=list)
    reasoning: Optional[str] = None
    severity: Optional[str] = "medium"

    model_config = ConfigDict(from_attributes=True)


class InspectionCreate(BaseModel):
    site_id: uuid.UUID = Field(..., description="Target site ID")
    summary: Optional[str] = Field(default=None, description="Optional field note or summary")


class InspectionListItem(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    site_name: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    status: str
    job_id: Optional[str] = None
    pass_rate: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InspectionDetailResponse(BaseModel):
    """Full inspection view matching Week 1 API contract:
    { inspection, media[], detections[], extractions[], findings[] }
    """
    inspection: InspectionListItem
    media: List[MediaItem] = Field(default_factory=list)
    detections: List[DetectionItem] = Field(default_factory=list)
    extractions: List[ExtractionItem] = Field(default_factory=list)
    findings: List[FindingItem] = Field(default_factory=list)
