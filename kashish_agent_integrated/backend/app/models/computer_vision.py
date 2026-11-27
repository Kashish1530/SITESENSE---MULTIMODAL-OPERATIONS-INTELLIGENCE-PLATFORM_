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
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin, ist_now

if TYPE_CHECKING:
    from app.models.inspections_media import Media
    from app.models.users_sites import Site


class Detection(Base, UUIDMixin):
    """Object detection result produced by Computer Vision YOLO models.
    Coordinates are stored strictly as [x1, y1, x2, y2] in absolute pixel coordinates.
    """

    __tablename__ = "detections"

    media_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Detected object class (person, safety_helmet, fire_extinguisher, pallet, etc.)",
    )
    bbox: Mapped[List[float]] = mapped_column(
        JSON,
        nullable=False,
        doc="Bounding box [x1, y1, x2, y2] in absolute pixel coordinates of original image",
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, doc="Detector model confidence score (0.0 - 1.0)"
    )
    zone: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, doc="Name of the spatial zone this detection falls within"
    )
    frame_no: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Frame index if detected from video media"
    )
    track_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Track ID if tracking is active"
    )
    model_version: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, doc="Model version string"
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSON, nullable=True, doc="OCR text or extra detection metadata"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=ist_now,
        nullable=False,
        doc="Timestamp in IST (UTC+05:30)",
    )

    # Relationships
    media: Mapped["Media"] = relationship("Media", back_populates="detections")


class TrackingResult(Base, UUIDMixin):
    """Temporal tracking metrics for video objects across frames."""

    __tablename__ = "tracking_results"

    media_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    track_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, doc="Unique track ID in the video"
    )
    class_name: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Object class tracked"
    )
    start_frame: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="Initial frame where track appeared"
    )
    end_frame: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="Last frame where track appeared"
    )
    dwell_time_seconds: Mapped[float] = mapped_column(
        Float, nullable=False, doc="Total duration object spent in camera view or zone"
    )
    trajectory: Mapped[Optional[List[Any]]] = mapped_column(
        JSON, nullable=True, doc="Centroid coordinates [[x, y, frame], ...] over time"
    )
    counting_line_crossed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, doc="Flag whether counting line was crossed"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=ist_now, nullable=False
    )

    # Relationships
    media: Mapped["Media"] = relationship("Media", back_populates="tracking_results")


class ZoneConfig(Base, UUIDMixin, TimestampMixin):
    """Spatial zones and counting lines defined per site or camera for compliance evaluation."""

    __tablename__ = "zone_configs"

    site_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    camera_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, doc="Optional camera identifier"
    )
    name: Mapped[str] = mapped_column(
        String(150), nullable=False, doc="Zone name (e.g., 'Emergency Exit Walkway A')"
    )
    zone_type: Mapped[str] = mapped_column(
        String(50),
        default="polygon",
        nullable=False,
        doc="Zone shape type: polygon | counting_line",
    )
    coordinates: Mapped[List[Any]] = mapped_column(
        JSON,
        nullable=False,
        doc="Array of points [[x, y], ...] defining the polygon or line vertices",
    )
    applicable_classes: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        doc="List of classes this zone evaluates (e.g. ['pallet', 'spill', 'person'])",
    )
    rules_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Zone parameters: clear_required, max_dwell_time_seconds, directional crossing",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, doc="Active status"
    )

    # Relationships
    site: Mapped["Site"] = relationship("Site", back_populates="zone_configs")
