from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.inspections import DetectionItem, FindingItem


class DetectionRunRequest(BaseModel):
    confidence_threshold: float = Field(default=0.25, ge=0.05, le=0.95, description="Detector confidence threshold")
    iou_threshold: float = Field(default=0.45, ge=0.1, le=0.9, description="NMS IoU threshold")
    save_annotated: bool = Field(default=True, description="Whether to render and save annotated image with bounding boxes")


class DetectionRunResponse(BaseModel):
    media_id: uuid.UUID
    inspection_id: uuid.UUID
    model_version: str = "yolo11s_sitesense_best3"
    total_detections: int
    detections: List[DetectionItem]
    class_counts: Dict[str, int]
    violations_detected: int
    annotated_media_url: Optional[str] = None
    inference_time_ms: float

    model_config = ConfigDict(from_attributes=True)


class InspectionDetectionRunResponse(BaseModel):
    inspection_id: uuid.UUID
    media_processed: int
    total_detections: int
    total_violations: int
    new_findings_count: int
    pass_rate: Optional[float]
    status: str
    detections: List[DetectionItem]
    findings: List[FindingItem] = Field(default_factory=list)
    class_counts: Dict[str, int]
    total_latency_ms: float

    model_config = ConfigDict(from_attributes=True)
