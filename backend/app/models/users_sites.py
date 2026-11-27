import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, Uuid
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

    serial_no: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Autoincrementing display sequence number"
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True, doc="User UUID identifier (mirrors id)"
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="Full display name"
    )
    first_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, doc="User given name"
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, doc="User family/surname"
    )
    supervision: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, doc="Supervisory role or manager title"
    )
    site_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, doc="Assigned primary site ID"
    )
    gender: Mapped[Optional[str]] = mapped_column(
        String(20), default="Unspecified", nullable=True, doc="Gender identity"
    )
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, doc="Contact telephone number"
    )
    is_valid: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False, doc="Identity validity check"
    )
    address: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, doc="Address object containing city, state, country, pincode"
    )
    city: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, doc="Address city"
    )
    state: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, doc="Address state or province"
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(100), default="United Kingdom", nullable=True, doc="Address country"
    )
    pincode: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, doc="Postal/PIN code"
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
    hashed_password: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, doc="Hashed password (mirrors password_hash)"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False, doc="Active status flag"
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="Timestamp of latest login"
    )

    def __init__(self, **kwargs: Any) -> None:
        if "full_name" in kwargs and "name" not in kwargs:
            kwargs["name"] = kwargs.pop("full_name")
        if "hashed_password" in kwargs and "password_hash" not in kwargs:
            kwargs["password_hash"] = kwargs.pop("hashed_password")
        if "password_hash" in kwargs and "hashed_password" not in kwargs:
            kwargs["hashed_password"] = kwargs["password_hash"]
        if "id" in kwargs and "user_id" not in kwargs:
            kwargs["user_id"] = kwargs["id"]
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

    serial_no: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Autoincrementing display sequence number"
    )
    site_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True, doc="Site UUID identifier (mirrors id)"
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, doc="Assigned site manager or lead user"
    )
    name: Mapped[str] = mapped_column(
        String(255), index=True, nullable=False, doc="Site name or identifier"
    )
    type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Site type (retail, warehouse, construction, service_centre, depot)",
    )
    city: Mapped[Optional[str]] = mapped_column(
        String(100), default="London", nullable=True, doc="City where site is situated"
    )
    state: Mapped[Optional[str]] = mapped_column(
        String(100), default="Greater London", nullable=True, doc="State or province"
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(100), default="United Kingdom", nullable=True, doc="Country location"
    )
    pincode: Mapped[Optional[str]] = mapped_column(
        String(20), default="E1 6AN", nullable=True, doc="Postal/PIN code"
    )
    location: Mapped[str] = mapped_column(
        String(255), default="Operational Zone", nullable=False, doc="Physical address or zone description"
    )
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False, doc="Active status of the site"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False, doc="Active status flag (mirrors active)"
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        doc="Optional metadata: GPS coordinates, operating hours, contact",
    )

    def __init__(self, **kwargs: Any) -> None:
        if "is_active" in kwargs and "active" not in kwargs:
            kwargs["active"] = kwargs["is_active"]
        if "active" in kwargs and "is_active" not in kwargs:
            kwargs["is_active"] = kwargs["active"]
        if "id" in kwargs and "site_id" not in kwargs:
            kwargs["site_id"] = kwargs["id"]
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
