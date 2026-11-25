from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db, require_field
from app.models.users_sites import User
from app.schemas.media import (
    MediaBatchUploadResponse,
    MediaResponse,
    MediaUploadResponse,
)
from app.services.media_service import MediaService
from app.schemas.detection import DetectionRunRequest, DetectionRunResponse
from app.services.detection_service import DetectionService

router = APIRouter()


@router.post(
    "/upload",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Inspection Media File",
    description="Uploads a single photo, video, or document (delivery note, permit) to an inspection session. Validates MIME type and extracts image dimensions.",
)
def upload_media_file(
    inspection_id: uuid.UUID = Form(..., description="ID of the inspection session"),
    file: UploadFile = File(..., description="Binary media file (jpg, png, mp4, mov, pdf)"),
    current_user: User = Depends(require_field),
    db: Session = Depends(get_db),
) -> MediaUploadResponse:
    """Upload media file to inspection session."""
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


@router.post(
    "/batch-upload",
    response_model=MediaBatchUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Batch Upload Multiple Media Files",
    description="Uploads multiple photos or documents in a single multipart request for high-efficiency field inspections.",
)
def batch_upload_media_files(
    inspection_id: uuid.UUID = Form(..., description="ID of the inspection session"),
    files: List[UploadFile] = File(..., description="List of binary files to upload"),
    current_user: User = Depends(require_field),
    db: Session = Depends(get_db),
) -> MediaBatchUploadResponse:
    """Batch upload multiple media files."""
    return MediaService.upload_batch(
        db=db,
        inspection_id=inspection_id,
        files=files,
        current_user=current_user,
    )


@router.get(
    "/{media_id}",
    response_model=MediaResponse,
    summary="Get Media Record Metadata",
    description="Retrieves metadata, storage path, dimensions, and download URL for an uploaded file.",
)
def get_media_metadata(
    media_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MediaResponse:
    """Retrieve media metadata."""
    return MediaService.get_media(db=db, media_id=media_id, current_user=current_user)


@router.get(
    "/{media_id}/download",
    response_class=FileResponse,
    summary="Download or Stream Media File",
    description="Streams original raw image, video, or document binary content from secure storage with appropriate Content-Type headers.",
)
def download_media_file(
    media_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Stream raw media file."""
    return MediaService.get_file_response(
        db=db,
        media_id=media_id,
        current_user=current_user,
        annotated=False,
    )


@router.get(
    "/{media_id}/file",
    response_class=FileResponse,
    include_in_schema=False,
)
def view_media_file_alias(
    media_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Alias for /download."""
    return MediaService.get_file_response(
        db=db,
        media_id=media_id,
        current_user=current_user,
        annotated=False,
    )


@router.get(
    "/{media_id}/annotated",
    response_class=FileResponse,
    summary="Download Annotated Media File",
    description="Streams the annotated image with rendered YOLO bounding boxes and clear-zone overlays, if available.",
)
def download_annotated_media(
    media_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Stream annotated media with bounding boxes."""
    return MediaService.get_file_response(
        db=db,
        media_id=media_id,
        current_user=current_user,
        annotated=True,
    )


@router.post(
    "/detect-direct",
    summary="Direct YOLO11s Detection on Uploaded Image File",
    description="Uploads an image, runs YOLO11s (best_3.pt) detection immediately, and returns real bounding boxes, counts, dimensions, and base64 annotated image.",
)
async def detect_direct_image(
    file: UploadFile = File(..., description="Image to analyze"),
    conf_threshold: float = Query(0.15, ge=0.05, le=0.95),
):
    """Direct inference on uploaded image file returning real bounding boxes and base64 annotated image."""
    content = await file.read()
    return DetectionService.detect_direct_file(
        file_bytes=content,
        filename=file.filename or "image.jpg",
        conf_threshold=conf_threshold,
    )


@router.post(
    "/{media_id}/detect",
    response_model=DetectionRunResponse,
    summary="Run YOLO11s Detection on Media",
    description="Executes YOLO11s (best_3.pt) safety object detection (16 classes) on the media file, evaluates spatial clear zones, renders bounding boxes, and persists detections.",
)
def run_media_detection(
    media_id: uuid.UUID,
    payload: DetectionRunRequest = DetectionRunRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DetectionRunResponse:
    """Run YOLO detection on this media asset."""
    result = DetectionService.detect_media(
        db=db,
        media_id=media_id,
        current_user=current_user,
        conf_threshold=payload.confidence_threshold,
        iou_threshold=payload.iou_threshold,
        save_annotated=payload.save_annotated,
    )
    return DetectionRunResponse(**result)


@router.delete(
    "/{media_id}",
    summary="Delete Media File",
    description="Permanently deletes the media record from PostgreSQL and removes physical binary files from disk.",
)
def delete_media_file(
    media_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete media file and record."""
    MediaService.delete_media(db=db, media_id=media_id, current_user=current_user)
    return {
        "message": "Media file deleted successfully",
        "media_id": str(media_id),
    }
