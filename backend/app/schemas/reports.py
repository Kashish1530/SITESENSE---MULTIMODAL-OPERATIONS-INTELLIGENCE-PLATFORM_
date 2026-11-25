from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ReportGenerateRequest(BaseModel):
    inspection_id: uuid.UUID = Field(..., description="Inspection ID to generate report for")
    format: str = Field(default="pdf", description="Target format: pdf | html | json")
    summary: Optional[str] = Field(default=None, description="Optional executive summary override")


class ReportResponse(BaseModel):
    id: uuid.UUID
    inspection_id: uuid.UUID
    format: str
    file_path: str
    file_size_bytes: int
    summary: Optional[str] = None
    generated_by: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
