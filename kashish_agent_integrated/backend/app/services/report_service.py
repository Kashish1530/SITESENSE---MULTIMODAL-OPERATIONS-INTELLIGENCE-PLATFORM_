import json
import os
from pathlib import Path
from typing import List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from app.config.settings import get_settings
from app.core.exceptions import NotFoundError
from app.models.inspections_media import Inspection
from app.models.knowledge_compliance import Finding
from app.models.system import Report
from app.models.users_sites import User
from app.schemas.reports import ReportGenerateRequest, ReportResponse

settings = get_settings()


class ReportService:
    """Service handling inspection report compilation, storage, and retrieval."""

    @classmethod
    def generate_report(
        cls, db: Session, current_user: User, payload: ReportGenerateRequest
    ) -> ReportResponse:
        """Generate a structured inspection compliance report."""
        inspection = db.query(Inspection).filter(Inspection.id == payload.inspection_id).first()
        if not inspection:
            raise NotFoundError(message=f"Inspection '{payload.inspection_id}' not found.")

        findings = db.query(Finding).filter(Finding.inspection_id == payload.inspection_id).all()
        total_findings = len(findings)
        passed_findings = sum(1 for f in findings if f.status == "pass")
        failed_findings = sum(1 for f in findings if f.status == "fail")

        summary_text = payload.summary or (
            f"Inspection Report for SiteSense ID {inspection.id}. "
            f"Evaluated {total_findings} compliance points: {passed_findings} passed, {failed_findings} failed. "
            f"Pass rate: {inspection.pass_rate if inspection.pass_rate is not None else 100.0}%."
        )

        # Prepare report storage directory
        reports_dir = Path(settings.MEDIA_STORAGE_PATH) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        report_file_name = f"report_{inspection.id}_{payload.format.lower()}.json"
        report_file_path = reports_dir / report_file_name

        report_content = {
            "report_id": str(uuid.uuid4()),
            "inspection_id": str(inspection.id),
            "site_id": str(inspection.site_id),
            "status": inspection.status,
            "pass_rate": inspection.pass_rate,
            "summary": summary_text,
            "findings_count": total_findings,
            "passed_count": passed_findings,
            "failed_count": failed_findings,
            "generated_by": str(current_user.id),
        }

        with open(report_file_path, "w", encoding="utf-8") as f:
            json.dump(report_content, f, indent=2)

        file_size = report_file_path.stat().st_size

        report = Report(
            inspection_id=payload.inspection_id,
            format=payload.format.lower(),
            file_path=str(report_file_path),
            file_size_bytes=file_size,
            summary=summary_text,
            generated_by=current_user.id,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return ReportResponse.model_validate(report)

    @classmethod
    def list_reports(
        cls,
        db: Session,
        *,
        inspection_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ReportResponse], int]:
        """List generated reports with pagination."""
        query = db.query(Report)
        if inspection_id:
            query = query.filter(Report.inspection_id == inspection_id)

        total = query.count()
        reports = query.order_by(Report.created_at.desc()).offset(offset).limit(limit).all()
        return [ReportResponse.model_validate(r) for r in reports], total

    @classmethod
    def get_report(cls, db: Session, report_id: uuid.UUID) -> ReportResponse:
        """Fetch report metadata by ID."""
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise NotFoundError(message=f"Report '{report_id}' not found.")
        return ReportResponse.model_validate(report)
