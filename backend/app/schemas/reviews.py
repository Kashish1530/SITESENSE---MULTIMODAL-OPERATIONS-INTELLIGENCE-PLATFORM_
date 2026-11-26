from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ReviewActionRequest(BaseModel):
    action: str = Field(..., description="Review outcome: accepted | corrected | rejected")
    corrected_value: Optional[Dict[str, Any]] = Field(default=None, description="Human corrected value if modified")
    reviewer_notes: Optional[str] = Field(default=None, description="Review feedback or rationale")


class ReviewCreate(BaseModel):
    item_type: str = Field(..., description="Target entity type: extraction | detection | finding")
    item_id: uuid.UUID = Field(..., description="ID of entity being reviewed")
    inspection_id: Optional[uuid.UUID] = Field(default=None, description="Optional linked inspection ID")
    original_value: Dict[str, Any] = Field(default_factory=dict, description="Original model output")
    corrected_value: Optional[Dict[str, Any]] = Field(default=None, description="Corrected value")
    action: str = Field(default="accepted", description="accepted | corrected | rejected")
    reviewer_notes: Optional[str] = Field(default=None, description="Reviewer feedback")


class ReviewResponse(BaseModel):
    id: uuid.UUID
    item_type: str
    item_id: uuid.UUID
    inspection_id: Optional[uuid.UUID] = None
    original_value: Dict[str, Any]
    corrected_value: Optional[Dict[str, Any]] = None
    action: str
    reviewer_id: uuid.UUID
    reviewer_notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ReviewQueueItem(BaseModel):
    id: uuid.UUID
    item_type: str = Field(..., description="extraction | detection | finding")
    inspection_id: Optional[uuid.UUID] = None
    site_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    severity: Optional[str] = None
    confidence_score: Optional[float] = None
    original_payload: Dict[str, Any] = Field(default_factory=dict)
    flagged_reason: str = Field(..., description="Reason sent to review queue (e.g., low confidence, rule violation)")
    created_at: Optional[datetime] = None
