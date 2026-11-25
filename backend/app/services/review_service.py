from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundError
from app.models.agent_review import Review
from app.models.computer_vision import Detection
from app.models.inspections_media import Inspection
from app.models.knowledge_compliance import Extraction, Finding
from app.models.users_sites import User
from app.schemas.reviews import ReviewActionRequest, ReviewCreate, ReviewQueueItem, ReviewResponse


class ReviewService:
    """Service managing human-in-the-loop review queue for detections, extractions, and findings."""

    @classmethod
    def get_queue(
        cls, db: Session, limit: int = 50, offset: int = 0
    ) -> Tuple[List[ReviewQueueItem], int]:
        """Fetch all items awaiting human review across detections, extractions, and findings."""
        items: List[ReviewQueueItem] = []

        # 1. Findings marked as "review"
        findings = db.query(Finding).filter(Finding.status == "review").all()
        for f in findings:
            insp = db.query(Inspection).filter(Inspection.id == f.inspection_id).first()
            items.append(
                ReviewQueueItem(
                    id=f.id,
                    item_type="finding",
                    inspection_id=f.inspection_id,
                    site_id=insp.site_id if insp else None,
                    title="Compliance Finding Pending Verification",
                    description=f.reasoning or "Rule evaluation flagged for human compliance verification",
                    severity=f.severity,
                    original_payload={"status": f.status, "rule_id": str(f.rule_id), "evidence": f.evidence_ids},
                    flagged_reason="Evaluation outcome uncertain; requires human sign-off",
                    created_at=f.created_at,
                )
            )

        # 2. Extractions pending review
        extractions = db.query(Extraction).filter(Extraction.status == "pending_review").all()
        for ext in extractions:
            insp_id = ext.media.inspection_id if ext.media else None
            items.append(
                ReviewQueueItem(
                    id=ext.id,
                    item_type="extraction",
                    inspection_id=insp_id,
                    title=f"Document Extraction: {ext.field_name}",
                    description=f"Field '{ext.field_name}' extracted with value '{ext.value}'",
                    confidence_score=ext.confidence,
                    original_payload={"field_name": ext.field_name, "value": ext.value, "media_id": str(ext.media_id)},
                    flagged_reason="OCR / Key-Value extraction awaiting field verification",
                    created_at=ext.created_at,
                )
            )

        # 3. Detections with low confidence (< 0.65)
        detections = db.query(Detection).filter(Detection.confidence < 0.65).limit(20).all()
        for det in detections:
            items.append(
                ReviewQueueItem(
                    id=det.id,
                    item_type="detection",
                    inspection_id=det.media.inspection_id if det.media else None,
                    title=f"Low-Confidence Object: {det.class_name}",
                    description=f"Confidence {round(det.confidence * 100, 1)}% below auto-verification threshold",
                    confidence_score=det.confidence,
                    original_payload={"bbox": det.bbox, "class_name": det.class_name},
                    flagged_reason="Vision detection confidence score is low",
                    created_at=det.created_at,
                )
            )

        total = len(items)
        paginated_items = items[offset : offset + limit]
        return paginated_items, total

    @classmethod
    def submit_review(
        cls, db: Session, current_user: User, payload: ReviewCreate
    ) -> ReviewResponse:
        """Submit a human review action and update the underlying entity."""
        review = Review(
            item_type=payload.item_type,
            item_id=payload.item_id,
            inspection_id=payload.inspection_id,
            original_value=payload.original_value,
            corrected_value=payload.corrected_value,
            action=payload.action.lower(),
            reviewer_id=current_user.id,
            reviewer_notes=payload.reviewer_notes,
        )
        db.add(review)

        # Apply state changes to underlying item
        if payload.item_type == "finding":
            finding = db.query(Finding).filter(Finding.id == payload.item_id).first()
            if finding:
                if payload.action.lower() == "accepted":
                    finding.status = "pass"
                elif payload.action.lower() in ("corrected", "rejected"):
                    finding.status = "fail"
        elif payload.item_type == "extraction":
            ext = db.query(Extraction).filter(Extraction.id == payload.item_id).first()
            if ext:
                ext.status = "approved" if payload.action.lower() == "accepted" else "corrected"
                ext.reviewed_by = current_user.id
                if payload.corrected_value and "value" in payload.corrected_value:
                    ext.value = str(payload.corrected_value["value"])

        db.commit()
        db.refresh(review)
        return ReviewResponse.model_validate(review)

    @classmethod
    def list_history(
        cls, db: Session, limit: int = 50, offset: int = 0
    ) -> Tuple[List[ReviewResponse], int]:
        """List review audit history."""
        query = db.query(Review)
        total = query.count()
        reviews = query.order_by(Review.created_at.desc()).offset(offset).limit(limit).all()
        return [ReviewResponse.model_validate(r) for r in reviews], total
