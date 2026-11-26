from typing import List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from app.api.deps import verify_site_access
from app.core.exceptions import ConflictError, NotFoundError
from app.models.inspections_media import Inspection
from app.models.computer_vision import ZoneConfig
from app.models.users_sites import Site, SiteMembership, User
from app.schemas.sites import SiteCreate, SiteDetailResponse, SiteResponse, SiteUpdate


class SiteService:
    """Service encapsulating database queries for Sites."""

    @classmethod
    def list_sites(
        cls,
        db: Session,
        current_user: User,
        *,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = True,
    ) -> Tuple[List[SiteResponse], int]:
        """List sites available to the user based on RBAC clearance."""
        query = db.query(Site)
        if active_only:
            query = query.filter(Site.active.is_(True))

        user_role = (current_user.role or "").lower()
        # Field and Reviewer users are filtered to sites where they have memberships
        if user_role not in ("admin", "manager"):
            query = query.join(
                SiteMembership,
                (SiteMembership.site_id == Site.id) & (SiteMembership.user_id == current_user.id),
            )

        total = query.count()
        sites = query.order_by(Site.name).offset(offset).limit(limit).all()

        responses = [SiteResponse.model_validate(s) for s in sites]
        return responses, total

    @classmethod
    def get_site(cls, db: Session, site_id: uuid.UUID, current_user: User) -> SiteDetailResponse:
        """Fetch single site detail and verify user has clearance."""
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            raise NotFoundError(message=f"Site '{site_id}' not found.")

        verify_site_access(site_id, current_user, db)

        total_inspections = db.query(Inspection).filter(Inspection.site_id == site_id).count()
        active_zones = db.query(ZoneConfig).filter(ZoneConfig.site_id == site_id, ZoneConfig.is_active.is_(True)).count()

        return SiteDetailResponse(
            id=site.id,
            name=site.name,
            type=site.type,
            location=site.location,
            active=site.active,
            metadata_json=site.metadata_json,
            created_at=site.created_at,
            updated_at=site.updated_at,
            total_inspections=total_inspections,
            active_zones_count=active_zones,
        )

    @classmethod
    def create_site(cls, db: Session, payload: SiteCreate) -> SiteResponse:
        """Create a new physical site (Admin only)."""
        existing = db.query(Site).filter(Site.name == payload.name.strip()).first()
        if existing:
            raise ConflictError(message=f"Site with name '{payload.name}' already exists.")

        site = Site(
            name=payload.name.strip(),
            type=payload.type.strip(),
            location=payload.location.strip(),
            active=payload.active,
            metadata_json=payload.metadata_json,
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        return SiteResponse.model_validate(site)

    @classmethod
    def update_site(cls, db: Session, site_id: uuid.UUID, payload: SiteUpdate) -> SiteResponse:
        """Update existing site details."""
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            raise NotFoundError(message=f"Site '{site_id}' not found.")

        if payload.name is not None:
            site.name = payload.name.strip()
        if payload.type is not None:
            site.type = payload.type.strip()
        if payload.location is not None:
            site.location = payload.location.strip()
        if payload.active is not None:
            site.active = payload.active
        if payload.metadata_json is not None:
            site.metadata_json = payload.metadata_json

        db.commit()
        db.refresh(site)
        return SiteResponse.model_validate(site)
