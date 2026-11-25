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
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.users_sites import Site, User
    from app.models.inspections_media import Inspection, Media
    from app.models.knowledge_compliance import Finding


class ChatSession(Base, UUIDMixin, TimestampMixin):
    """Conversational sessions between users and the agentic system."""

    __tablename__ = "chat_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional site context for the session",
    )
    title: Mapped[str] = mapped_column(
        String(255), default="New Conversation", nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )
    agent_runs: Mapped[List["AgentRun"]] = relationship(
        "AgentRun", back_populates="session"
    )


class ChatMessage(Base, UUIDMixin):
    """Individual conversational turns with multimodal attachments and grounded citations."""

    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, doc="Message author role: user | assistant | system"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Textual content of the message"
    )
    attached_media_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media.id", ondelete="SET NULL"),
        nullable=True,
        doc="Optional attached image or document for multimodal questions",
    )
    attachment_metadata: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Metadata for attached multimodal files (photo, video, pdf, excel)",
    )
    citations: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Grounded evidence citations: source_file, page, clause, detection_ids",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
    attached_media: Mapped[Optional["Media"]] = relationship("Media")


class AgentRun(Base, UUIDMixin):
    """Audit log and metrics for an individual agent execution loop."""

    __tablename__ = "agent_runs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question: Mapped[str] = mapped_column(
        Text, nullable=False, doc="User prompt or question posed to the agent"
    )
    route: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Router decision: vision | policy | database | multimodal | direct",
    )
    tools_called: Mapped[Optional[List[Any]]] = mapped_column(
        JSON, nullable=True, doc="JSONB array of tools invoked during the run"
    )
    tokens: Mapped[Optional[int]] = mapped_column(
        Integer, default=0, nullable=True, doc="Total LLM tokens consumed"
    )
    cost: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 6), default=0.0, nullable=True, doc="Calculated financial cost of this run in USD"
    )
    latency: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 3), default=0.0, nullable=True, doc="Total duration in milliseconds"
    )
    status: Mapped[str] = mapped_column(
        String(50), default="success", server_default="success", nullable=True, doc="Status: success | error"
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __init__(self, **kwargs: Any) -> None:
        if "total_tokens" in kwargs and "tokens" not in kwargs:
            kwargs["tokens"] = kwargs.pop("total_tokens")
        if "estimated_cost_usd" in kwargs and "cost" not in kwargs:
            kwargs["cost"] = kwargs.pop("estimated_cost_usd")
        if "latency_ms" in kwargs and "latency" not in kwargs:
            kwargs["latency"] = kwargs.pop("latency_ms")
        super().__init__(**kwargs)

    # Relationships
    session: Mapped[Optional["ChatSession"]] = relationship("ChatSession", back_populates="agent_runs")
    tool_calls: Mapped[List["AgentToolCall"]] = relationship(
        "AgentToolCall", back_populates="agent_run", cascade="all, delete-orphan"
    )


class AgentToolCall(Base, UUIDMixin):
    """Step-by-step trace of every tool invocation performed by the ReAct agent."""

    __tablename__ = "agent_tool_calls"

    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Invoked tool (e.g. search_policies, analyse_media, query_database, raise_ticket)",
    )
    tool_args: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False, doc="Arguments supplied to the tool"
    )
    tool_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, doc="Structured result / observation returned by the tool"
    )
    latency_ms: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False, doc="Tool execution time in ms"
    )
    is_error: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, doc="True if tool execution raised an error"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    agent_run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="tool_calls")


class Review(Base, UUIDMixin):
    """Human review actions over low-confidence extractions, detections, or findings."""

    __tablename__ = "reviews"

    item_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Target entity type: extraction | detection | finding",
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
        doc="UUID of the reviewed row",
    )
    inspection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    original_value: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False, doc="Original model output"
    )
    corrected_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, doc="Human corrected value"
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Review action: accepted | corrected | rejected",
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="ID of human reviewer who made the decision",
    )
    reviewer_notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Optional feedback or notes from reviewer"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    reviewer: Mapped["User"] = relationship("User", back_populates="reviews")


class Ticket(Base, UUIDMixin):
    """Remediation and maintenance tickets.
    Agent may propose tickets, but human approval is mandatory before activation.
    """

    __tablename__ = "tickets"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inspection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, default="", doc="Ticket title"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default="", doc="Remediation description"
    )
    priority: Mapped[Optional[str]] = mapped_column(
        String(50), default="medium", server_default="medium", nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="proposed",
        nullable=False,
        index=True,
        doc="Status: proposed | approved | rejected | resolved",
    )
    proposed_by_agent: Mapped[Optional[bool]] = mapped_column(
        Boolean, default=False, server_default="false", nullable=True
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who created or triggered ticket creation",
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Human manager/admin who approved the proposed ticket",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="Approval timestamp in UTC"
    )

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="tickets")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])
