import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db, require_admin
from app.schemas.zones import SiteZonesSummary, ZoneConfigCreate, ZoneConfigResponse
from app.services.zone_service import ZoneService

router = APIRouter()


@router.get(
    "",
    response_model=SiteZonesSummary,
    summary="Get Spatial Zones and Counting Lines for a Site",
    description="Returns polygon clear zones and counting lines configured for a site or camera angle.",
)
def get_zones(
    site_id: uuid.UUID = Query(..., description="Target site ID"),
    _user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SiteZonesSummary:
    """Retrieve spatial zones for site."""
    return ZoneService.get_zones_for_site(db, site_id)


@router.post(
    "",
    response_model=ZoneConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save Zone Configuration (Admin Only)",
    description="Saves a new polygon zone or counting line for a site with target classes and rules.",
)
def save_zone(
    payload: ZoneConfigCreate,
    _user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> ZoneConfigResponse:
    """Save zone or line geometry."""
    return ZoneService.save_zone(db, payload)
