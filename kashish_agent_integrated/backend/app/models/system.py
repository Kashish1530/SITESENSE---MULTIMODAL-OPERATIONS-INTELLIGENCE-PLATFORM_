import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
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
    from app.models.users_sites import User
    from app.models.inspections_media import Inspection


class Report(Base, UUIDMixin, TimestampMixin):
    """Generated inspection reports (PDF/HTML/JSON) with embedded evidence and citations."""

    __tablename__ = "reports"

    inspection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    format: Mapped[str] = mapped_column(
        String(20), default="pdf", nullable=False, doc="Report format: pdf | html | json"
    )
    file_path: Mapped[str] = mapped_column(
        String(1024), nullable=False, doc="Storage path to the generated report file outside PostgreSQL"
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, doc="File size in bytes"
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Executive summary included in the report"
    )
    generated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who triggered report generation",
    )

    # Relationships
    inspection: Mapped["Inspection"] = relationship("Inspection", back_populates="reports")
    generator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[generated_by])


class Notification(Base, UUIDMixin):
    """User notifications for events (reviews required, approvals needed, jobs completed)."""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, doc="Notification title"
    )
    message: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Notification content body"
    )
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Type: review_needed | inspection_complete | ticket_approval | alert",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, doc="Read status flag"
    )
    link_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, doc="Optional UI link to navigate to"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User")


class AuditLog(Base, UUIDMixin):
    """System-wide audit trail recording actions, reviews, approvals, and mutations."""

    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User who initiated the action (null if automated background worker)",
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Action identifier: upload_media | approve_ticket | correct_review | update_rule | agent_run",
    )
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Target domain entity: inspection | ticket | review | rule | media | policy",
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
        doc="Primary key of the affected entity",
    )
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, doc="Structured payload of the change / action"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, doc="Client IP address"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, doc="Client browser / agent user string"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
