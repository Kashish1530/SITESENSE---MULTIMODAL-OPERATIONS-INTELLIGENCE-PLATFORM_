"""
models.py
---------
Pydantic data models for OCR inputs and outputs.
These define the exact shape of every JSON response the module produces.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class OCRTextResult(BaseModel):
    """A single recognised text region."""
    text: str = Field(..., description="Recognised text string")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Recognition confidence (0–1)")
    bounding_box: List[List[int]] = Field(
        ...,
        description="4 corner points [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] in pixel coordinates"
    )


class OCRResponse(BaseModel):
    """Full OCR response for one image."""
    success: bool
    image_name: str
    extracted_text: List[OCRTextResult] = Field(default_factory=list)
    full_text: str = ""
    processing_time_ms: float = 0.0
    error: Optional[str] = None
    preprocessing_meta: Optional[dict] = None


class OCRRequest(BaseModel):
    """Optional structured request for programmatic use."""
    image_path: str
    min_confidence: float = 0.3
    enable_preprocessing: bool = True
