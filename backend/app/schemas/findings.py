from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class FindingCreate(BaseModel):
    inspection_id: uuid.UUID = Field(..., description="Inspection ID where finding was observed")
    rule_id: uuid.UUID = Field(..., description="Compliance rule ID being evaluated")
    status: str = Field(default="fail", description="Compliance outcome: pass | fail | review")
    evidence_ids: List[str] = Field(default_factory=list, description="List of UUID strings pointing to media/detections")
    reasoning: Optional[str] = Field(default=None, description="Explanation for the determination")
    severity: str = Field(default="medium", description="Severity level: low | medium | high | critical")


class FindingUpdate(BaseModel):
    status: Optional[str] = Field(default=None, description="Updated status: pass | fail | review")
    severity: Optional[str] = Field(default=None, description="Updated severity: low | medium | high | critical")
    reasoning: Optional[str] = Field(default=None, description="Updated reasoning")
    evidence_ids: Optional[List[str]] = Field(default=None, description="Updated evidence list")


class FindingResponse(BaseModel):
    id: uuid.UUID
    inspection_id: uuid.UUID
    rule_id: uuid.UUID
    status: str
    evidence_ids: List[str] = Field(default_factory=list)
    reasoning: Optional[str] = None
    severity: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
