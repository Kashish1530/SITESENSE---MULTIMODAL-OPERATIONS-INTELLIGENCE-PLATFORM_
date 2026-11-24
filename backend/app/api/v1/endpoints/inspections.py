from datetime import datetime
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db, require_field
from app.models.users_sites import User
from app.schemas.common import PaginatedResponse
from app.schemas.inspections import (
    InspectionCreate,
    InspectionDetailResponse,
    InspectionListItem,
)
from app.schemas.media import MediaResponse, MediaUploadResponse
from app.services.inspection_service import InspectionService
from app.services.media_service import MediaService
from app.schemas.detection import DetectionRunRequest, InspectionDetectionRunResponse
from app.services.detection_service import DetectionService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[InspectionListItem],
    summary="List and Filter Inspections",
    description="Lists inspection sessions with optional filtering by site_id, status, and date range.",
)
def list_inspections(
    site_id: Optional[uuid.UUID] = Query(None, description="Filter by site ID"),
    status: Optional[str] = Query(None, description="Filter by status (pending, processing, completed, failed)"),
    from_date: Optional[datetime] = Query(None, description="Start date filter (UTC)"),
    to_date: Optional[datetime] = Query(None, description="End date filter (UTC)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[InspectionListItem]:
    """List inspection records with pagination and filters."""
    items, total = InspectionService.list_inspections(
        db,
        current_user,
        site_id=site_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{inspection_id}",
    response_model=InspectionDetailResponse,
    summary="Get Full Inspection with Evidence & Detections",
    description="Returns the inspection session together with all associated media, YOLO detections, document extractions, and compliance rule findings.",
)
def get_inspection(
    inspection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InspectionDetailResponse:
    """Retrieve full inspection details."""
    return InspectionService.get_inspection_detail(db, inspection_id, current_user)


@router.post(
    "",
    response_model=InspectionListItem,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Inspection Session",
    description="Initializes a new inspection session for a site. Field users and Admins may create inspections.",
)
def create_inspection(
    payload: InspectionCreate,
    current_user: User = Depends(require_field),
    db: Session = Depends(get_db),
) -> InspectionListItem:
    """Create an inspection session."""
    return InspectionService.create_inspection(db, current_user, payload)


@router.post(
    "/{inspection_id}/media",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Media Directly to Inspection",
    description="Uploads photo, video, or PDF directly attached to this inspection session.",
)
def upload_inspection_media(
    inspection_id: uuid.UUID,
    file: UploadFile = File(..., description="File to upload"),
    current_user: User = Depends(require_field),
    db: Session = Depends(get_db),
) -> MediaUploadResponse:
    """Upload media file to this inspection session."""
    media_res = MediaService.upload_media(
        db=db,
        inspection_id=inspection_id,
        file=file,
        current_user=current_user,
    )
    return MediaUploadResponse(
        media=media_res,
        message=f"File '{media_res.filename}' successfully uploaded and stored.",
    )


@router.get(
    "/{inspection_id}/media",
    response_model=List[MediaResponse],
    summary="List Media Attached to Inspection",
    description="Returns all media files and metadata for this inspection session.",
)
def list_inspection_media(
    inspection_id: uuid.UUID,
    type: Optional[str] = Query(None, description="Filter by type (image, video, doc)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MediaResponse]:
    """List media items for this inspection."""
    return MediaService.list_media_for_inspection(
        db=db,
        inspection_id=inspection_id,
        current_user=current_user,
        media_type=type,
    )


@router.post(
    "/{inspection_id}/detect",
    response_model=InspectionDetectionRunResponse,
    summary="Run YOLO11s Detection on Entire Inspection Session",
    description="Batch runs YOLO11s (best_3.pt) safety detection across all media frames in this inspection, updates compliance pass rate, and logs findings.",
)
def run_inspection_detection(
    inspection_id: uuid.UUID,
    payload: DetectionRunRequest = DetectionRunRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InspectionDetectionRunResponse:
    """Run YOLO detection across all media in this inspection session."""
    result = DetectionService.detect_inspection(
        db=db,
        inspection_id=inspection_id,
        current_user=current_user,
        conf_threshold=payload.confidence_threshold,
        iou_threshold=payload.iou_threshold,
    )
    return InspectionDetectionRunResponse(**result)



