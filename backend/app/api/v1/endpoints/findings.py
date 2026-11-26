from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db, require_manager
from app.models.users_sites import User
from app.schemas.common import PaginatedResponse
from app.schemas.findings import FindingCreate, FindingResponse, FindingUpdate
from app.services.finding_service import FindingService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[FindingResponse],
    summary="List Compliance Findings",
    description="Returns compliance evaluation outcomes with optional filters for inspection ID, status, and severity.",
)
def list_findings(
    inspection_id: Optional[uuid.UUID] = Query(None, description="Filter by inspection ID"),
    status: Optional[str] = Query(None, description="Filter by status (pass, fail, review)"),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high, critical)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[FindingResponse]:
    """List compliance findings with pagination and filters."""
    items, total = FindingService.list_findings(
        db,
        inspection_id=inspection_id,
        status=status,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{finding_id}",
    response_model=FindingResponse,
    summary="Get Finding Detail",
    description="Retrieves a single compliance finding with linked evidence IDs and reasoning.",
)
def get_finding(
    finding_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FindingResponse:
    """Retrieve finding details by UUID."""
    return FindingService.get_finding(db, finding_id)


@router.post(
    "",
    response_model=FindingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Compliance Finding",
    description="Records a new compliance finding linked to an inspection and rule evaluation.",
)
def create_finding(
    payload: FindingCreate,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FindingResponse:
    """Create a new compliance finding."""
    return FindingService.create_finding(db, payload)


@router.patch(
    "/{finding_id}",
    response_model=FindingResponse,
    summary="Update Finding Status or Severity",
    description="Modifies a finding status, severity, or reasoning (Requires Manager or Admin role).",
)
def update_finding(
    finding_id: uuid.UUID,
    payload: FindingUpdate,
    _manager: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> FindingResponse:
    """Update finding properties."""
    return FindingService.update_finding(db, finding_id, payload)
