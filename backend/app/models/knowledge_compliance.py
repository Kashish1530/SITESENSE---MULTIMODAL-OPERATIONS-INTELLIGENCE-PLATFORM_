import uuid
from datetime import datetime, date
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Date,
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
    from app.models.inspections_media import Inspection, Media
    from app.models.users_sites import User
    from app.models.agent_review import Ticket


class Policy(Base, UUIDMixin):
    """Company policies, compliance handbooks, and regulatory documents."""

    __tablename__ = "policies"

    title: Mapped[str] = mapped_column(
        String(255), index=True, nullable=False, doc="Policy document title"
    )
    version: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="Document version (e.g., 'v2026.1')"
    )
    source_file: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Original document filename or path"
    )
    effective_date: Mapped[date] = mapped_column(
        Date, nullable=False, doc="Date the policy became effective"
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True, doc="Storage path to external policy document"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="active", server_default="active", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="Record creation timestamp in UTC",
    )

    # Relationships
    chunks: Mapped[List["PolicyChunk"]] = relationship(
        "PolicyChunk", back_populates="policy", cascade="all, delete-orphan"
    )
    rules: Mapped[List["Rule"]] = relationship(
        "Rule", back_populates="policy"
    )


class PolicyChunk(Base, UUIDMixin):
    """Chunked passages from policy documents with metadata for hybrid retrieval."""

    __tablename__ = "policy_chunks"

    policy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="Zero-indexed chunk sequence order"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Extracted chunk text passage"
    )
    page_number: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="Source page number in policy document"
    )
    section_heading: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, doc="Section heading hierarchy"
    )
    embedding_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True, doc="Vector store reference ID in Chroma/pgvector"
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, doc="Chunk metadata: token count, keywords, headers"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    policy: Mapped["Policy"] = relationship("Policy", back_populates="chunks")


class Extraction(Base, UUIDMixin):
    """Structured fields extracted from documents (delivery notes, permits, invoices)."""

    __tablename__ = "extractions"

    media_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Extracted field name (e.g. delivery_note_no, permit_expiry, vendor)",
    )
    value: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Extracted string/serialized value"
    )
    value_type: Mapped[str] = mapped_column(
        String(50), default="string", server_default="string", nullable=True
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, doc="Extraction confidence score (0.0 - 1.0)"
    )
    status: Mapped[str] = mapped_column(
        String(50), default="pending_review", server_default="pending_review", nullable=True
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reviewer user ID if manually verified or corrected",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="Creation timestamp in UTC",
    )

    def __init__(self, **kwargs: Any) -> None:
        if "extracted_value" in kwargs and "value" not in kwargs:
            kwargs["value"] = kwargs.pop("extracted_value")
        super().__init__(**kwargs)

    @property
    def extracted_value(self) -> str:
        return self.value

    @extracted_value.setter
    def extracted_value(self, val: str) -> None:
        self.value = val

    # Relationships
    media: Mapped["Media"] = relationship("Media", back_populates="extractions")
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by])


class Rule(Base, UUIDMixin):
    """Machine-readable compliance rules evaluated against detections and extractions."""

    __tablename__ = "rules"

    name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, doc="Rule identifier name"
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Human-readable rule explanation"
    )
    rule_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Type: required_object | forbidden_object | count_threshold | clear_zone | dwell_time | document_match",
    )
    parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        doc="Rule parameters (JSONB in Postgres)",
    )
    policy_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Authoritative policy clause reference",
    )
    policy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("policies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(50), default="high", server_default="high", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    policy: Mapped[Optional["Policy"]] = relationship("Policy", back_populates="rules")
    findings: Mapped[List["Finding"]] = relationship(
        "Finding", back_populates="rule"
    )


class Finding(Base, UUIDMixin):
    """The result of evaluating a rule against detections or extractions."""

    __tablename__ = "findings"

    inspection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rules.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Compliance outcome: pass | fail | review",
    )
    evidence_ids: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        doc="List of UUID strings pointing to detection, media, or extraction evidence (JSONB)",
    )
    reasoning: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Explanation for the pass/fail determination"
    )
    severity: Mapped[str] = mapped_column(
        String(50), default="medium", server_default="medium", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    inspection: Mapped["Inspection"] = relationship("Inspection", back_populates="findings")
    rule: Mapped["Rule"] = relationship("Rule", back_populates="findings")
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket", back_populates="finding"
    )
