from typing import List
import uuid
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundError
from app.models.computer_vision import ZoneConfig
from app.models.users_sites import Site
from app.schemas.zones import SiteZonesSummary, ZoneConfigCreate, ZoneConfigResponse


class ZoneService:
    """Service encapsulating database queries for Site Zones and Counting Lines."""

    @classmethod
    def get_zones_for_site(cls, db: Session, site_id: uuid.UUID) -> SiteZonesSummary:
        """Retrieve all spatial zones and counting lines for a given site."""
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            raise NotFoundError(message=f"Site '{site_id}' not found.")

        configs = db.query(ZoneConfig).filter(ZoneConfig.site_id == site_id, ZoneConfig.is_active.is_(True)).all()

        zones = [ZoneConfigResponse.model_validate(z) for z in configs if z.zone_type == "polygon"]
        lines = [ZoneConfigResponse.model_validate(z) for z in configs if z.zone_type == "counting_line"]

        return SiteZonesSummary(site_id=site_id, zones=zones, lines=lines)

    @classmethod
    def save_zone(cls, db: Session, payload: ZoneConfigCreate) -> ZoneConfigResponse:
        """Save a new polygon zone or counting line (Admin only)."""
        site = db.query(Site).filter(Site.id == payload.site_id).first()
        if not site:
            raise NotFoundError(message=f"Site '{payload.site_id}' not found.")

        zone = ZoneConfig(
            site_id=payload.site_id,
            camera_id=payload.camera_id,
            name=payload.name.strip(),
            zone_type=payload.zone_type.strip(),
            coordinates=payload.coordinates,
            applicable_classes=payload.applicable_classes,
            rules_config=payload.rules_config,
            is_active=payload.is_active,
        )
        db.add(zone)
        db.commit()
        db.refresh(zone)
        return ZoneConfigResponse.model_validate(zone)
