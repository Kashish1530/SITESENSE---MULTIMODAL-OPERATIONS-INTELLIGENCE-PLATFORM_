from datetime import datetime
from typing import List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from app.api.deps import verify_site_access
from app.core.exceptions import NotFoundError
from app.models.computer_vision import Detection
from app.models.inspections_media import Inspection, Media
from app.models.knowledge_compliance import Extraction, Finding, Rule
from app.models.users_sites import Site, SiteMembership, User
from app.schemas.inspections import (
    DetectionItem,
    ExtractionItem,
    FindingItem,
    InspectionCreate,
    InspectionDetailResponse,
    InspectionListItem,
    MediaItem,
)


class InspectionService:
    """Service encapsulating database queries for Inspections."""

    @classmethod
    def list_inspections(
        cls,
        db: Session,
        current_user: User,
        *,
        site_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[InspectionListItem], int]:
        """List inspections with optional filters, scoped to user role permissions."""
        query = db.query(Inspection, Site.name.label("site_name")).join(Site, Site.id == Inspection.site_id)

        user_role = (current_user.role or "").lower()
        if user_role not in ("admin", "manager"):
            query = query.join(
                SiteMembership,
                (SiteMembership.site_id == Inspection.site_id) & (SiteMembership.user_id == current_user.id),
            )

        if site_id:
            query = query.filter(Inspection.site_id == site_id)
        if status:
            query = query.filter(Inspection.status == status.strip().lower())
        if from_date:
            query = query.filter(Inspection.created_at >= from_date)
        if to_date:
            query = query.filter(Inspection.created_at <= to_date)

        total = query.count()
        rows = query.order_by(Inspection.created_at.desc()).offset(offset).limit(limit).all()

        results: List[InspectionListItem] = []
        for insp, site_name in rows:
            results.append(
                InspectionListItem(
                    id=insp.id,
                    site_id=insp.site_id,
                    site_name=site_name,
                    user_id=insp.user_id,
                    status=insp.status,
                    job_id=insp.job_id,
                    pass_rate=insp.pass_rate,
                    created_at=insp.created_at,
                )
            )

        return results, total

    @classmethod
    def get_inspection_detail(
        cls, db: Session, inspection_id: uuid.UUID, current_user: User
    ) -> InspectionDetailResponse:
        """Return complete inspection session with media, detections, extractions, and findings."""
        insp_row = (
            db.query(Inspection, Site.name.label("site_name"))
            .join(Site, Site.id == Inspection.site_id)
            .filter(Inspection.id == inspection_id)
            .first()
        )
        if not insp_row:
            raise NotFoundError(message=f"Inspection '{inspection_id}' not found.")

        insp, site_name = insp_row
        verify_site_access(insp.site_id, current_user, db)

        # 1. Fetch Media items
        media_records = db.query(Media).filter(Media.inspection_id == inspection_id).all()
        media_items = [
            MediaItem(
                id=m.id,
                inspection_id=m.inspection_id,
                type=m.type,
                path=m.path,
                filename=m.filename,
                is_annotated=m.is_annotated,
                annotated_path=m.annotated_path,
                created_at=m.created_at,
            )
            for m in media_records
        ]
        media_ids = [m.id for m in media_records]

        # 2. Fetch Detections
        detections: List[DetectionItem] = []
        if media_ids:
            det_records = db.query(Detection).filter(Detection.media_id.in_(media_ids)).all()
            detections = [
                DetectionItem(
                    id=d.id,
                    media_id=d.media_id,
                    class_name=d.class_name,
                    bbox=d.bbox,
                    confidence=d.confidence,
                    zone=d.zone,
                    frame_no=d.frame_no,
                )
                for d in det_records
            ]

        # 3. Fetch Extractions
        extractions: List[ExtractionItem] = []
        if media_ids:
            ext_records = db.query(Extraction).filter(Extraction.media_id.in_(media_ids)).all()
            extractions = [
                ExtractionItem(
                    id=e.id,
                    media_id=e.media_id,
                    field_name=e.field_name,
                    value=e.value,
                    confidence=e.confidence,
                    status=e.status,
                    reviewed_by=e.reviewed_by,
                )
                for e in ext_records
            ]

        # 4. Fetch Findings with rule names
        finding_records = (
            db.query(Finding, Rule.name.label("rule_name"))
            .join(Rule, Rule.id == Finding.rule_id)
            .filter(Finding.inspection_id == inspection_id)
            .all()
        )
        findings = [
            FindingItem(
                id=f.id,
                inspection_id=f.inspection_id,
                rule_id=f.rule_id,
                rule_name=rule_name,
                status=f.status,
                evidence_ids=f.evidence_ids or [],
                reasoning=f.reasoning,
                severity=f.severity,
            )
            for f, rule_name in finding_records
        ]

        inspection_summary = InspectionListItem(
            id=insp.id,
            site_id=insp.site_id,
            site_name=site_name,
            user_id=insp.user_id,
            status=insp.status,
            job_id=insp.job_id,
            pass_rate=insp.pass_rate,
            created_at=insp.created_at,
        )

        return InspectionDetailResponse(
            inspection=inspection_summary,
            media=media_items,
            detections=detections,
            extractions=extractions,
            findings=findings,
        )

    @classmethod
    def create_inspection(
        cls, db: Session, current_user: User, payload: InspectionCreate
    ) -> InspectionListItem:
        """Create a new inspection session record."""
        site = db.query(Site).filter(Site.id == payload.site_id).first()
        if not site:
            raise NotFoundError(message=f"Site '{payload.site_id}' not found.")

        verify_site_access(payload.site_id, current_user, db)

        inspection = Inspection(
            site_id=payload.site_id,
            user_id=current_user.id,
            status="pending",
            summary=payload.summary,
        )
        db.add(inspection)
        db.commit()
        db.refresh(inspection)

        return InspectionListItem(
            id=inspection.id,
            site_id=inspection.site_id,
            site_name=site.name,
            user_id=inspection.user_id,
            status=inspection.status,
            job_id=inspection.job_id,
            pass_rate=inspection.pass_rate,
            created_at=inspection.created_at,
        )
