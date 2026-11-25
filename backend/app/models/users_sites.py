import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.inspections_media import Inspection
    from app.models.computer_vision import ZoneConfig
    from app.models.agent_review import ChatSession, Review
    from app.models.system import AuditLog


class User(Base, UUIDMixin, TimestampMixin):
    """User accounts with role-based access control (Admin, Manager, Field, Reviewer)."""

    __tablename__ = "users"

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="Full display name"
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False, doc="Unique email address"
    )
    role: Mapped[str] = mapped_column(
        String(50),
        default="field",
        nullable=False,
        doc="User role: admin | manager | field | reviewer",
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, doc="Bcrypt / Argon2 hashed password"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False, doc="Active status flag"
    )

    def __init__(self, **kwargs: Any) -> None:
        if "full_name" in kwargs and "name" not in kwargs:
            kwargs["name"] = kwargs.pop("full_name")
        if "hashed_password" in kwargs and "password_hash" not in kwargs:
            kwargs["password_hash"] = kwargs.pop("hashed_password")
        super().__init__(**kwargs)

    @property
    def full_name(self) -> str:
        return self.name

    @full_name.setter
    def full_name(self, value: str) -> None:
        self.name = value

    @property
    def hashed_password(self) -> Optional[str]:
        return self.password_hash

    @hashed_password.setter
    def hashed_password(self, value: Optional[str]) -> None:
        self.password_hash = value

    # Relationships
    site_memberships: Mapped[List["SiteMembership"]] = relationship(
        "SiteMembership", back_populates="user", cascade="all, delete-orphan"
    )
    inspections: Mapped[List["Inspection"]] = relationship(
        "Inspection", back_populates="inspector"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession", back_populates="user"
    )
    reviews: Mapped[List["Review"]] = relationship(
        "Review", back_populates="reviewer"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )


class Site(Base, UUIDMixin, TimestampMixin):
    """Physical locations, stores, warehouses, construction sites, and depots."""

    __tablename__ = "sites"

    name: Mapped[str] = mapped_column(
        String(255), index=True, nullable=False, doc="Site name or identifier"
    )
    type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Site type (retail, warehouse, construction, service_centre, depot)",
    )
    location: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="Physical address or zone description"
    )
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False, doc="Active status of the site"
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        doc="Optional metadata: GPS coordinates, operating hours, contact",
    )

    def __init__(self, **kwargs: Any) -> None:
        if "is_active" in kwargs and "active" not in kwargs:
            kwargs["active"] = kwargs.pop("is_active")
        super().__init__(**kwargs)

    @property
    def is_active(self) -> bool:
        return self.active

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self.active = value

    # Relationships
    memberships: Mapped[List["SiteMembership"]] = relationship(
        "SiteMembership", back_populates="site", cascade="all, delete-orphan"
    )
    inspections: Mapped[List["Inspection"]] = relationship(
        "Inspection", back_populates="site"
    )
    zone_configs: Mapped[List["ZoneConfig"]] = relationship(
        "ZoneConfig", back_populates="site", cascade="all, delete-orphan"
    )


class SiteMembership(Base, UUIDMixin):
    """Associates users with sites and defines site-scoped access control."""

    __tablename__ = "site_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "site_id", name="uq_user_site_membership"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_override: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, doc="Optional site-level role override"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="Membership assignment date in UTC",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="site_memberships")
    site: Mapped["Site"] = relationship("Site", back_populates="memberships")


class RefreshToken(Base, UUIDMixin):
    """Stores active JWT refresh tokens with revocation support."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(
        String(500), unique=True, index=True, nullable=False, doc="Cryptographic token string"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, doc="Token expiry timestamp in UTC"
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, doc="Revocation flag"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
