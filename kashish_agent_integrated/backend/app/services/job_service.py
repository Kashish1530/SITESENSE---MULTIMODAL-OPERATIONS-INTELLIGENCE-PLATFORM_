from typing import List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundError
from app.models.inspections_media import Job
from app.schemas.jobs import JobCreate, JobResponse


class JobService:
    """Service handling asynchronous background jobs and execution status."""

    @classmethod
    def get_job(cls, db: Session, job_id: uuid.UUID) -> JobResponse:
        """Fetch an individual job by its UUID."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError(message=f"Job '{job_id}' not found.")
        return JobResponse.model_validate(job)

    @classmethod
    def list_jobs(
        cls,
        db: Session,
        *,
        inspection_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[JobResponse], int]:
        """List jobs with pagination and optional filters."""
        query = db.query(Job)
        if inspection_id:
            query = query.filter(Job.inspection_id == inspection_id)
        if status:
            query = query.filter(Job.status == status.strip().lower())

        total = query.count()
        jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
        return [JobResponse.model_validate(j) for j in jobs], total

    @classmethod
    def create_job(cls, db: Session, payload: JobCreate) -> JobResponse:
        """Enqueue a new processing job."""
        job = Job(
            inspection_id=payload.inspection_id,
            job_type=payload.job_type,
            status="queued",
            progress=0,
            current_stage="queued_for_worker",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return JobResponse.model_validate(job)
