from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.users_sites import User
from app.schemas.common import PaginatedResponse
from app.schemas.jobs import JobCreate, JobResponse
from app.services.job_service import JobService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[JobResponse],
    summary="List Background Jobs",
    description="Lists asynchronous ingestion, inference, and reporting jobs with optional status filter.",
)
def list_jobs(
    inspection_id: Optional[uuid.UUID] = Query(None, description="Filter by inspection ID"),
    status: Optional[str] = Query(None, description="Filter by status (queued, processing, completed, failed)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[JobResponse]:
    """List asynchronous processing jobs."""
    items, total = JobService.list_jobs(
        db,
        inspection_id=inspection_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get Job Execution Status",
    description="Retrieves live job execution state, progress percentage, current stage, and results.",
)
def get_job_status(
    job_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Retrieve job progress and status by UUID."""
    return JobService.get_job(db, job_id)


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enqueue Asynchronous Job",
    description="Triggers a new asynchronous processing job (inspection ingestion, CV inference, or reporting).",
)
def enqueue_job(
    payload: JobCreate,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Trigger an async processing job."""
    return JobService.create_job(db, payload)
