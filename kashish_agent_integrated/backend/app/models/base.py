import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

IST = timezone(timedelta(hours=5, minutes=30))


def ist_now() -> datetime:
    """Return current timezone-aware datetime in Indian Standard Time (UTC+05:30)."""
    return datetime.now(IST)


class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy ORM models in SiteSense."""
    pass


class UUIDMixin:
    """Standard mixin providing a UUID v4 primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Unique UUID primary key",
    )


class TimestampMixin:
    """Standard audit timestamps mixin for tables (all timestamps in IST / UTC+05:30)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=ist_now,
        nullable=False,
        doc="Record creation timestamp in IST (UTC+05:30)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=ist_now,
        onupdate=ist_now,
        nullable=False,
        doc="Record last update timestamp in IST (UTC+05:30)",
    )
