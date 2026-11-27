from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import RoleChecker, get_db
from app.models.users_sites import User
from app.schemas.common import PaginatedResponse
from app.schemas.reviews import ReviewCreate, ReviewQueueItem, ReviewResponse
from app.services.review_service import ReviewService

router = APIRouter()
require_review_access = RoleChecker(["admin", "manager", "reviewer"])


@router.get(
    "/queue",
    response_model=PaginatedResponse[ReviewQueueItem],
    summary="Get Human Review Queue",
    description="Returns items requiring human verification (low-confidence CV detections, unverified findings, OCR extractions).",
)
def get_review_queue(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(require_review_access),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ReviewQueueItem]:
    """List pending review items."""
    items, total = ReviewService.get_queue(db, limit=limit, offset=offset)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Human Review Action",
    description="Records human review decision (accepted, corrected, rejected) with optional notes and updates underlying entity.",
)
def submit_review(
    payload: ReviewCreate,
    current_user: User = Depends(require_review_access),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    """Submit human review decision."""
    return ReviewService.submit_review(db, current_user, payload)


@router.get(
    "/history",
    response_model=PaginatedResponse[ReviewResponse],
    summary="Review Audit History",
    description="Lists past human review actions with decisions and reviewer notes.",
)
def list_review_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(require_review_access),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ReviewResponse]:
    """List past review actions."""
    items, total = ReviewService.list_history(db, limit=limit, offset=offset)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
