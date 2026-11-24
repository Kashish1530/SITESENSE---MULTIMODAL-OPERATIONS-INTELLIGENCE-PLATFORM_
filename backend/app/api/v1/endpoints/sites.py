from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db, require_admin
from app.models.users_sites import User
from app.schemas.common import PaginatedResponse
from app.schemas.sites import SiteCreate, SiteDetailResponse, SiteResponse, SiteUpdate
from app.services.site_service import SiteService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[SiteResponse],
    summary="List Accessible Sites",
    description="Returns all sites visible to the authenticated user. Admins and Managers see all sites; Field users see only assigned sites.",
)
def list_sites(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[SiteResponse]:
    """List physical sites with pagination."""
    items, total = SiteService.list_sites(
        db, current_user, limit=limit, offset=offset, active_only=active_only
    )
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{site_id}",
    response_model=SiteDetailResponse,
    summary="Get Site Details",
    description="Returns detailed information for a physical site including active zone counts and inspection stats.",
)
def get_site(
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SiteDetailResponse:
    """Retrieve site by ID."""
    return SiteService.get_site(db, site_id, current_user)


@router.post(
    "",
    response_model=SiteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Site (Admin Only)",
    description="Registers a new physical location, warehouse, or retail store in the system.",
)
def create_site(
    payload: SiteCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SiteResponse:
    """Register a new site."""
    return SiteService.create_site(db, payload)


@router.put(
    "/{site_id}",
    response_model=SiteResponse,
    summary="Update Site Details (Admin Only)",
    description="Updates physical location details, type, or active status.",
)
def update_site(
    site_id: uuid.UUID,
    payload: SiteUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SiteResponse:
    """Update site attributes."""
    return SiteService.update_site(db, site_id, payload)
