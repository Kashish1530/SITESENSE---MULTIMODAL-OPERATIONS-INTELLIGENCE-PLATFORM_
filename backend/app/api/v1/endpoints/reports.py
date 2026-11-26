import os
from pathlib import Path
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db, require_manager
from app.core.exceptions import NotFoundError
from app.models.users_sites import User
from app.schemas.common import PaginatedResponse
from app.schemas.reports import ReportGenerateRequest, ReportResponse
from app.services.report_service import ReportService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[ReportResponse],
    summary="List Inspection Reports",
    description="Lists generated compliance reports with optional inspection ID filter.",
)
def list_reports(
    inspection_id: Optional[uuid.UUID] = Query(None, description="Filter by inspection ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ReportResponse]:
    """List generated inspection reports."""
    items, total = ReportService.list_reports(
        db, inspection_id=inspection_id, limit=limit, offset=offset
    )
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "/generate",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Inspection Report",
    description="Compiles compliance findings, pass rate, and media evidence into an official report (Manager or Admin).",
)
def generate_report(
    payload: ReportGenerateRequest,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Generate a new inspection compliance report."""
    return ReportService.generate_report(db, current_user, payload)


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Get Report Metadata",
    description="Retrieves metadata, summary, file size, and timestamps for a generated report.",
)
def get_report(
    report_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Retrieve report metadata by ID."""
    return ReportService.get_report(db, report_id)


@router.get(
    "/{report_id}/download",
    summary="Download Generated Report File",
    description="Streams the raw report file (PDF, HTML, or JSON) directly to the client.",
)
def download_report(
    report_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download the generated report artifact."""
    report = ReportService.get_report(db, report_id)
    file_path = Path(report.file_path)
    if not file_path.exists():
        raise NotFoundError(message=f"Report file '{file_path.name}' not found on storage disk.")

    media_type = "application/json" if report.format == "json" else "application/pdf"
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=media_type,
    )
