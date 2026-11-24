import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.users_sites import Site, User
    from app.models.computer_vision import Detection, TrackingResult
    from app.models.knowledge_compliance import Extraction, Finding
    from app.models.system import Report


class Inspection(Base, UUIDMixin):
    """An inspection session from one physical site visit."""

    __tablename__ = "inspections"

    site_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Inspected site ID",
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Uploading field user / inspector",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
        doc="Status: pending | processing | completed | failed | under_review",
    )
    job_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Associated background ingestion job ID",
    )
    pass_rate: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, doc="Overall percentage of compliance checks passed"
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Executive summary of findings"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="Record creation timestamp in UTC",
    )

    # Relationships
    site: Mapped["Site"] = relationship("Site", back_populates="inspections")
    inspector: Mapped[Optional["User"]] = relationship("User", back_populates="inspections")
    media_items: Mapped[List["Media"]] = relationship(
        "Media", back_populates="inspection", cascade="all, delete-orphan"
    )
    findings: Mapped[List["Finding"]] = relationship(
        "Finding", back_populates="inspection", cascade="all, delete-orphan"
    )
    jobs: Mapped[List["Job"]] = relationship(
        "Job", back_populates="inspection", cascade="all, delete-orphan"
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report", back_populates="inspection", cascade="all, delete-orphan"
    )


class Media(Base, UUIDMixin):
    """Uploaded files (photos, videos, delivery notes, permits)."""

    __tablename__ = "media"

    inspection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Media type: image | video | doc",
    )
    path: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Storage path or S3/MinIO key for the file"
    )
    filename: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, default="", doc="Original uploaded filename"
    )
    mime_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, default="image/jpeg", doc="MIME type"
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=0, doc="File size in bytes"
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        doc="Device metadata, EXIF GPS coordinates, video duration/FPS",
    )
    is_annotated: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    annotated_path: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True
    )
    quality_flag: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="Upload timestamp in UTC",
    )

    def __init__(self, **kwargs: Any) -> None:
        if "storage_path" in kwargs and "path" not in kwargs:
            kwargs["path"] = kwargs.pop("storage_path")
        super().__init__(**kwargs)

    @property
    def storage_path(self) -> str:
        return self.path

    @storage_path.setter
    def storage_path(self, value: str) -> None:
        self.path = value

    # Relationships
    inspection: Mapped["Inspection"] = relationship("Inspection", back_populates="media_items")
    detections: Mapped[List["Detection"]] = relationship(
        "Detection", back_populates="media", cascade="all, delete-orphan"
    )
    extractions: Mapped[List["Extraction"]] = relationship(
        "Extraction", back_populates="media", cascade="all, delete-orphan"
    )
    tracking_results: Mapped[List["TrackingResult"]] = relationship(
        "TrackingResult", back_populates="media", cascade="all, delete-orphan"
    )


class Job(Base, UUIDMixin, TimestampMixin):
    """Asynchronous background jobs for inspection ingestion, inference, and reporting."""

    __tablename__ = "jobs"

    inspection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(
        String(50),
        default="inspection_ingestion",
        nullable=False,
        doc="Job type (inspection_ingestion, document_extraction, report_generation)",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="queued",
        nullable=False,
        index=True,
        doc="Job status: queued | processing | completed | failed",
    )
    progress: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, doc="Progress indicator percentage (0 - 100)"
    )
    current_stage: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Stage description (e.g., preprocessing, vision_detection, rule_evaluation)",
    )
    result_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, doc="Structured result payload or summary on job completion"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Error message on job failure"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="Job processing start timestamp"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="Job completion timestamp"
    )

    # Relationships
    inspection: Mapped[Optional["Inspection"]] = relationship("Inspection", back_populates="jobs")
