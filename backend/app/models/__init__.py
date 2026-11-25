"""SiteSense unified ORM models.
Organized into 6 core operational groups:
A. User and site management (User, Site, SiteMembership, RefreshToken)
B. Inspection and media (Inspection, Media, Job)
C. Computer Vision (Detection, TrackingResult, ZoneConfig)
D. Knowledge and compliance (Policy, PolicyChunk, Extraction, Rule, Finding)
E. Agent and human review (ChatSession, ChatMessage, AgentRun, AgentToolCall, Review, Ticket)
F. System management (Report, Notification, AuditLog)
"""

from app.models.base import Base, TimestampMixin, UUIDMixin

# Group A: User and site management
from app.models.users_sites import (
    RefreshToken,
    Site,
    SiteMembership,
    User,
)

# Group B: Inspection and media
from app.models.inspections_media import (
    Inspection,
    Job,
    Media,
)

# Group C: Computer Vision
from app.models.computer_vision import (
    Detection,
    TrackingResult,
    ZoneConfig,
)

# Group D: Knowledge and compliance
from app.models.knowledge_compliance import (
    Extraction,
    Finding,
    Policy,
    PolicyChunk,
    Rule,
)

# Group E: Agent and human review
from app.models.agent_review import (
    AgentRun,
    AgentToolCall,
    ChatMessage,
    ChatSession,
    Review,
    Ticket,
)

# Group F: System management
from app.models.system import (
    AuditLog,
    Notification,
    Report,
)

__all__ = [
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    # Group A
    "User",
    "Site",
    "SiteMembership",
    "RefreshToken",
    # Group B
    "Inspection",
    "Media",
    "Job",
    # Group C
    "Detection",
    "TrackingResult",
    "ZoneConfig",
    # Group D
    "Policy",
    "PolicyChunk",
    "Extraction",
    "Rule",
    "Finding",
    # Group E
    "ChatSession",
    "ChatMessage",
    "AgentRun",
    "AgentToolCall",
    "Review",
    "Ticket",
    # Group F
    "Report",
    "Notification",
    "AuditLog",
]
