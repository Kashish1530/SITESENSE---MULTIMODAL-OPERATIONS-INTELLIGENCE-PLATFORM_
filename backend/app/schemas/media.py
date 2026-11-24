from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class MediaResponse(BaseModel):
    """Schema representing an uploaded media record."""

    id: uuid.UUID
    inspection_id: uuid.UUID
    type: str = Field(..., description="Media type: image | video | doc")
    path: str = Field(..., description="Relative storage path")
    filename: Optional[str] = Field(default=None, description="Original uploaded filename")
    mime_type: Optional[str] = Field(default=None, description="MIME type")
    file_size_bytes: Optional[int] = Field(default=0, description="File size in bytes")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Device, EXIF, dimensions, video FPS, or SHA256 checksum"
    )
    is_annotated: bool = Field(default=False, description="Whether visual bounding boxes are rendered")
    annotated_path: Optional[str] = Field(default=None, description="Storage path for annotated image")
    download_url: str = Field(..., description="Direct API download link")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MediaUploadResponse(BaseModel):
    """Response returned upon successful single file upload."""

    media: MediaResponse
    message: str = "Media uploaded successfully"
    job_id: Optional[str] = Field(default=None, description="ID of queued background analysis job")


class MediaBatchUploadResponse(BaseModel):
    """Response returned upon batch media upload."""

    uploaded: List[MediaResponse]
    total_uploaded: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
