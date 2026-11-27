from typing import List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundError
from app.models.inspections_media import Inspection
from app.models.knowledge_compliance import Finding, Rule
from app.schemas.findings import FindingCreate, FindingResponse, FindingUpdate


class FindingService:
    """Service handling compliance findings and defect outcomes."""

    @classmethod
    def get_finding(cls, db: Session, finding_id: uuid.UUID) -> FindingResponse:
        """Fetch a specific compliance finding by UUID."""
        finding = db.query(Finding).filter(Finding.id == finding_id).first()
        if not finding:
            raise NotFoundError(message=f"Finding '{finding_id}' not found.")
        return FindingResponse.model_validate(finding)

    @classmethod
    def list_findings(
        cls,
        db: Session,
        *,
        inspection_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[FindingResponse], int]:
        """List compliance findings with optional filters."""
        query = db.query(Finding)
        if inspection_id:
            query = query.filter(Finding.inspection_id == inspection_id)
        if status:
            query = query.filter(Finding.status == status.strip().lower())
        if severity:
            query = query.filter(Finding.severity == severity.strip().lower())

        total = query.count()
        findings = query.order_by(Finding.created_at.desc()).offset(offset).limit(limit).all()
        return [FindingResponse.model_validate(f) for f in findings], total

    @classmethod
    def create_finding(cls, db: Session, payload: FindingCreate) -> FindingResponse:
        """Create a new finding linked to an inspection and rule."""
        inspection = db.query(Inspection).filter(Inspection.id == payload.inspection_id).first()
        if not inspection:
            raise NotFoundError(message=f"Inspection '{payload.inspection_id}' not found.")

        rule = db.query(Rule).filter(Rule.id == payload.rule_id).first()
        if not rule:
            raise NotFoundError(message=f"Rule '{payload.rule_id}' not found.")

        finding = Finding(
            inspection_id=payload.inspection_id,
            rule_id=payload.rule_id,
            status=payload.status.lower(),
            evidence_ids=payload.evidence_ids,
            reasoning=payload.reasoning,
            severity=payload.severity.lower(),
        )
        db.add(finding)
        db.commit()
        db.refresh(finding)
        return FindingResponse.model_validate(finding)

    @classmethod
    def update_finding(cls, db: Session, finding_id: uuid.UUID, payload: FindingUpdate) -> FindingResponse:
        """Update an existing finding's status, severity, or reasoning."""
        finding = db.query(Finding).filter(Finding.id == finding_id).first()
        if not finding:
            raise NotFoundError(message=f"Finding '{finding_id}' not found.")

        if payload.status is not None:
            finding.status = payload.status.lower()
        if payload.severity is not None:
            finding.severity = payload.severity.lower()
        if payload.reasoning is not None:
            finding.reasoning = payload.reasoning
        if payload.evidence_ids is not None:
            finding.evidence_ids = payload.evidence_ids

        db.commit()
        db.refresh(finding)
        return FindingResponse.model_validate(finding)
