"""SQLAlchemy ORM models for the Site Text Intelligence (OCR + Intelligence) schema."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, ist_now

JSONVariant = JSON().with_variant(JSONB(), "postgresql")

ENTITY_TYPE_VALUES = (
    "equipment_id",
    "serial_number",
    "model_number",
    "pallet_tag",
    "sku_code",
    "rack_location",
    "quantity",
    "capacity_rating",
    "inspection_date",
    "expiry_date",
    "safety_signage",
    "certification",
    "barcode_data",
    "qr_data",
    "general_text",
)
ENTITY_TYPE_CHECK = (
    "entity_type IN ("
    + ", ".join(f"'{val}'" for val in ENTITY_TYPE_VALUES)
    + ")"
)
VERIFICATION_STATUS_CHECK = (
    "verification_status IN ('auto_approved', 'needs_review', 'rejected')"
)
CONFIDENCE_CHECK = "confidence >= 0.0 AND confidence <= 1.0"


class SiteTextReport(Base):
    """Top-level OCR + intelligence record (one row per uploaded image)."""

    __tablename__ = "ocr_reports"
    __table_args__ = (
        CheckConstraint("processing_time_ms >= 0", name="ck_ocr_reports_proc_ms"),
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    site_id: Mapped[str] = mapped_column(
        String(255),
        default="SITE-DEFAULT",
        server_default="SITE-DEFAULT",
        nullable=False,
        index=True,
    )
    inspection_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    media_name: Mapped[str] = mapped_column(String(512), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=ist_now,
        nullable=False,
        index=True,
    )
    full_text: Mapped[str] = mapped_column(
        Text, default="", server_default="", nullable=False
    )
    translated_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_translated: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    processing_time_ms: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0", nullable=False
    )
    annotated_image_base64: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    entities: Mapped[List["SiteTextEntity"]] = relationship(
        "SiteTextEntity", back_populates="report", cascade="all, delete-orphan"
    )
    review_queue_items: Mapped[List["SiteTextReviewQueue"]] = relationship(
        "SiteTextReviewQueue", back_populates="report", cascade="all, delete-orphan"
    )
    compliance_checks: Mapped[List["SiteTextComplianceCheck"]] = relationship(
        "SiteTextComplianceCheck", back_populates="report", cascade="all, delete-orphan"
    )
    genai_contexts: Mapped[List["SiteTextGenAIContext"]] = relationship(
        "SiteTextGenAIContext", back_populates="report", cascade="all, delete-orphan"
    )


class SiteTextEntity(Base):
    """Extracted OCR entity row linked to a top-level ocr_reports record."""

    __tablename__ = "ocr_entities"
    __table_args__ = (
        CheckConstraint(ENTITY_TYPE_CHECK, name="ck_ocr_entities_entity_type"),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_ocr_entities_confidence"),
        CheckConstraint(
            VERIFICATION_STATUS_CHECK, name="ck_ocr_entities_verification_status"
        ),
    )

    entity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ocr_reports.report_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bounding_box: Mapped[List[List[float]]] = mapped_column(
        JSONVariant, default=list, server_default="[]", nullable=False
    )
    verification_status: Mapped[str] = mapped_column(
        String(50),
        default="needs_review",
        server_default="needs_review",
        nullable=False,
        index=True,
    )
    review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    report: Mapped["SiteTextReport"] = relationship(
        "SiteTextReport", back_populates="entities"
    )


class SiteTextReviewQueue(Base):
    """Human validation queue mirroring SiteTextEntity columns plus review_status."""

    __tablename__ = "ocr_review_queue"
    __table_args__ = (
        CheckConstraint(ENTITY_TYPE_CHECK, name="ck_ocr_review_queue_entity_type"),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_ocr_review_queue_confidence"),
        CheckConstraint(
            VERIFICATION_STATUS_CHECK,
            name="ck_ocr_review_queue_verification_status",
        ),
        CheckConstraint(
            "review_status IS NULL OR review_status IN ('pending', 'approved', 'rejected')",
            name="ck_ocr_review_queue_review_status",
        ),
    )

    entity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ocr_reports.report_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bounding_box: Mapped[List[List[float]]] = mapped_column(
        JSONVariant, default=list, server_default="[]", nullable=False
    )
    verification_status: Mapped[str] = mapped_column(
        String(50),
        default="needs_review",
        server_default="needs_review",
        nullable=False,
        index=True,
    )
    review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        default="pending",
        server_default="pending",
        nullable=True,
        index=True,
    )

    report: Mapped["SiteTextReport"] = relationship(
        "SiteTextReport", back_populates="review_queue_items"
    )


class SiteTextComplianceCheck(Base):
    """Rule evaluation outcome per OCR report."""

    __tablename__ = "ocr_compliance_checks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('compliant', 'non_compliant', 'flagged', 'insufficient_data')",
            name="ck_ocr_compliance_checks_status",
        ),
    )

    check_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ocr_reports.report_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    report: Mapped["SiteTextReport"] = relationship(
        "SiteTextReport", back_populates="compliance_checks"
    )


class SiteTextGenAIContext(Base):
    """Optional LLM grounding prompt and metadata linked to an ocr_reports record."""

    __tablename__ = "ocr_genai_contexts"

    context_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ocr_reports.report_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSONVariant, default=dict, server_default="{}", nullable=False
    )

    report: Mapped["SiteTextReport"] = relationship(
        "SiteTextReport", back_populates="genai_contexts"
    )
