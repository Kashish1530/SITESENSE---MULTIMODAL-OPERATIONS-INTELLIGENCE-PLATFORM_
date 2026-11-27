from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    inspection_id: Optional[uuid.UUID] = Field(default=None, description="Inspection ID being processed")
    job_type: str = Field(
        default="inspection_ingestion",
        description="Type of job: inspection_ingestion | document_extraction | report_generation | vision_inference",
    )


class JobResponse(BaseModel):
    id: uuid.UUID
    inspection_id: Optional[uuid.UUID] = None
    job_type: str
    status: str = Field(..., description="Job status: queued | processing | completed | failed")
    progress: int = Field(default=0, ge=0, le=100, description="Progress percentage")
    current_stage: Optional[str] = None
    result_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
