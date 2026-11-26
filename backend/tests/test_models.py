import uuid
from datetime import date, datetime, timezone
import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models import (
    AgentRun,
    AgentToolCall,
    AuditLog,
    ChatMessage,
    ChatSession,
    Detection,
    Extraction,
    Finding,
    Inspection,
    Job,
    Media,
    Notification,
    Policy,
    PolicyChunk,
    RefreshToken,
    Report,
    Review,
    Rule,
    Site,
    SiteMembership,
    Ticket,
    TrackingResult,
    User,
    ZoneConfig,
)


@pytest.fixture(scope="module")
def db_session():
    """Provides a transactional database session for model testing."""
    Base.metadata.create_all(bind=engine)
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_all_24_tables_registered_and_created():
    """Verify all 24 required database tables exist in the schema."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    expected_tables = {
        # Group A
        "users", "sites", "site_memberships", "refresh_tokens",
        # Group B
        "inspections", "media", "jobs",
        # Group C
        "detections", "tracking_results", "zone_configs",
        # Group D
        "policies", "policy_chunks", "extractions", "rules", "findings",
        # Group E
        "chat_sessions", "chat_messages", "agent_runs", "agent_tool_calls", "reviews", "tickets",
        # Group F
        "reports", "notifications", "audit_logs"
    }

    missing = expected_tables - table_names
    assert not missing, f"Missing tables in database: {missing}"


def test_group_a_users_and_sites(db_session: Session):
    """Verify Group A: users, sites, site_memberships, refresh_tokens."""
    # 1. Create User
    user = User(
        email=f"inspector_{uuid.uuid4().hex[:6]}@sitesense.io",
        hashed_password="argon2_hashed_secret",
        full_name="Jane Field Inspector",
        role="field",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    assert isinstance(user.id, uuid.UUID)
    assert user.created_at is not None

    # 2. Create Site
    site = Site(
        name="London Central Depot 04",
        type="warehouse",
        location="Zone 4 Industrial Park, London",
        metadata_json={"gps": {"lat": 51.5074, "lng": -0.1278}, "operating_hours": "24/7"},
    )
    db_session.add(site)
    db_session.flush()

    assert isinstance(site.id, uuid.UUID)

    # 3. Create SiteMembership
    membership = SiteMembership(
        user_id=user.id,
        site_id=site.id,
        role_override="lead_inspector",
    )
    db_session.add(membership)
    db_session.flush()

    assert membership.user.email == user.email
    assert membership.site.name == site.name

    # 4. Create RefreshToken
    token = RefreshToken(
        user_id=user.id,
        token="jwt_refresh_token_cryptographic_sample",
        expires_at=datetime.now(timezone.utc),
        revoked=False,
    )
    db_session.add(token)
    db_session.flush()

    assert token.user.id == user.id


def test_group_b_inspections_and_media(db_session: Session):
    """Verify Group B: inspections, media, and background jobs."""
    # Create required user and site
    user = User(
        email=f"field_{uuid.uuid4().hex[:6]}@sitesense.io",
        hashed_password="hashed_pass",
        full_name="John Field",
        role="field",
    )
    site = Site(name="Site 7 Distribution Hub", type="warehouse", location="Building 7")
    db_session.add_all([user, site])
    db_session.flush()

    # 1. Inspection
    inspection = Inspection(
        site_id=site.id,
        user_id=user.id,
        status="processing",
        summary="Weekly safety and walkway compliance inspection for Site 7",
    )
    db_session.add(inspection)
    db_session.flush()
    assert isinstance(inspection.id, uuid.UUID)

    # 2. Media (Confirming original and annotated files stored externally)
    media = Media(
        inspection_id=inspection.id,
        type="image",
        filename="aisle_4_walkway.jpg",
        storage_path="/data/storage/sites/7/inspections/raw/aisle_4_walkway.jpg",
        mime_type="image/jpeg",
        file_size_bytes=2048500,
        metadata_json={"camera": "iPhone 15 Pro", "resolution": [4032, 3024]},
        is_annotated=True,
        annotated_path="/data/storage/sites/7/inspections/annotated/aisle_4_walkway_boxed.jpg",
        quality_flag="valid",
    )
    db_session.add(media)
    db_session.flush()
    assert media.inspection.id == inspection.id

    # 3. Job
    job = Job(
        inspection_id=inspection.id,
        job_type="inspection_ingestion",
        status="processing",
        progress=65,
        current_stage="vision_inference",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(job)
    db_session.flush()
    assert job.inspection.id == inspection.id


def test_group_c_computer_vision(db_session: Session):
    """Verify Group C: detections, tracking_results, zone_configs.
    Confirms bbox stored as [x1, y1, x2, y2] absolute pixel coordinates.
    """
    site = Site(name="Site 12 Retail Store", type="retail", location="Main Street")
    db_session.add(site)
    db_session.flush()

    inspection = Inspection(site_id=site.id, status="completed")
    db_session.add(inspection)
    db_session.flush()

    media = Media(
        inspection_id=inspection.id,
        type="image",
        filename="entrance.jpg",
        storage_path="/storage/entrance.jpg",
        mime_type="image/jpeg",
        file_size_bytes=1024000,
    )
    db_session.add(media)
    db_session.flush()

    # 1. Detection with xyxy absolute coordinates
    detection = Detection(
        media_id=media.id,
        class_name="fire_extinguisher",
        bbox=[120.0, 340.0, 250.0, 680.0],  # [x1, y1, x2, y2]
        confidence=0.94,
        zone="Emergency Access Corridor",
        model_version="yolov8x-sitesense-v1.2",
        metadata_json={"ocr_text": "EXP: 11/2027"},
    )
    db_session.add(detection)
    db_session.flush()
    assert detection.bbox == [120.0, 340.0, 250.0, 680.0]
    assert detection.media.id == media.id

    # 2. TrackingResult
    tracking = TrackingResult(
        media_id=media.id,
        track_id=104,
        class_name="person",
        start_frame=1,
        end_frame=150,
        dwell_time_seconds=18.5,
        trajectory=[[100, 200, 1], [105, 210, 15], [120, 220, 30]],
        counting_line_crossed=True,
    )
    db_session.add(tracking)
    db_session.flush()
    assert tracking.track_id == 104

    # 3. ZoneConfig
    zone = ZoneConfig(
        site_id=site.id,
        camera_id="cam_retail_01",
        name="Emergency Exit Clear Zone",
        zone_type="polygon",
        coordinates=[[100, 100], [500, 100], [500, 400], [100, 400]],
        applicable_classes=["pallet", "box", "debris"],
        rules_config={"clear_required": True, "max_dwell_seconds": 0},
    )
    db_session.add(zone)
    db_session.flush()
    assert zone.site.id == site.id


def test_group_d_knowledge_and_compliance(db_session: Session):
    """Verify Group D: policies, policy_chunks, extractions, rules, findings.
    Confirms finding links to evidence IDs and policy references.
    """
    # 1. Policy
    policy = Policy(
        title="Walkway and Exit Clearance Regulations",
        version="v2.1",
        source_file="HSE_Walkway_Policy_2026.pdf",
        file_path="/storage/policies/HSE_Walkway_Policy_2026.pdf",
        effective_date=date(2026, 1, 1),
        status="active",
    )
    db_session.add(policy)
    db_session.flush()

    # 2. PolicyChunk (Passage only, NOT the whole PDF)
    chunk = PolicyChunk(
        policy_id=policy.id,
        chunk_index=0,
        content="Clause 4.2.1: All pedestrian walkways and emergency fire exit passages must remain free of obstruction at all times.",
        page_number=14,
        section_heading="4.2 Walkway and Corridor Maintenance",
        embedding_id="vec_chunk_847192",
    )
    db_session.add(chunk)
    db_session.flush()
    assert chunk.policy.id == policy.id

    # 3. Rule
    rule = Rule(
        policy_id=policy.id,
        name="Walkway Obstruction Rule",
        description="Detects pallets, boxes, or equipment blocking designated walkways",
        rule_type="forbidden_object",
        parameters={"forbidden_classes": ["pallet", "spill", "blocked_exit"], "zone": "walkway"},
        policy_ref="Clause 4.2.1",
        severity="critical",
    )
    db_session.add(rule)
    db_session.flush()

    # Setup Inspection and Media for Extraction & Finding
    site = Site(name="Site B Depot", type="depot", location="North Yard")
    db_session.add(site)
    db_session.flush()
    inspection = Inspection(site_id=site.id, status="completed")
    db_session.add(inspection)
    db_session.flush()
    media = Media(
        inspection_id=inspection.id,
        type="doc",
        filename="delivery_note_042.pdf",
        storage_path="/storage/delivery_note_042.pdf",
        mime_type="application/pdf",
        file_size_bytes=350000,
    )
    db_session.add(media)
    db_session.flush()

    # 4. Extraction
    extraction = Extraction(
        media_id=media.id,
        field_name="delivery_note_no",
        extracted_value="DN-2026-9812",
        value_type="string",
        confidence=0.72,  # Low confidence -> pending_review
        status="pending_review",
    )
    db_session.add(extraction)
    db_session.flush()
    assert extraction.status == "pending_review"

    # 5. Finding with linked evidence IDs
    finding = Finding(
        inspection_id=inspection.id,
        rule_id=rule.id,
        status="fail",
        evidence_ids=[str(media.id), str(extraction.id)],
        reasoning="Pallet detected obstructing fire exit walkway in violation of Clause 4.2.1",
        severity="critical",
    )
    db_session.add(finding)
    db_session.flush()
    assert finding.rule.name == "Walkway Obstruction Rule"
    assert finding.inspection.id == inspection.id


def test_group_e_agent_and_human_review(db_session: Session):
    """Verify Group E: chat_sessions, chat_messages, agent_runs, agent_tool_calls, reviews, tickets.
    Confirms human approval workflow on proposed tickets.
    """
    user = User(
        email=f"manager_{uuid.uuid4().hex[:6]}@sitesense.io",
        hashed_password="pw",
        full_name="Alex Manager",
        role="manager",
    )
    reviewer = User(
        email=f"reviewer_{uuid.uuid4().hex[:6]}@sitesense.io",
        hashed_password="pw",
        full_name="Sam Reviewer",
        role="reviewer",
    )
    site = Site(name="Site C Retail", type="retail", location="Downtown")
    db_session.add_all([user, reviewer, site])
    db_session.flush()

    inspection = Inspection(site_id=site.id, status="completed")
    db_session.add(inspection)
    db_session.flush()

    rule = Rule(
        name="Fire Extinguisher Expiry Rule",
        description="Verify extinguisher inspected within 12 months",
        rule_type="document_match",
        parameters={"max_age_months": 12},
        policy_ref="Policy HSE 2.3",
        severity="high",
    )
    db_session.add(rule)
    db_session.flush()

    finding = Finding(
        inspection_id=inspection.id,
        rule_id=rule.id,
        status="fail",
        evidence_ids=[],
        reasoning="Extinguisher expired 3 months ago",
        severity="high",
    )
    db_session.add(finding)
    db_session.flush()

    # 1. ChatSession & ChatMessage
    session = ChatSession(user_id=user.id, site_id=site.id, title="Site C Walkway Inquiry")
    db_session.add(session)
    db_session.flush()

    msg = ChatMessage(
        session_id=session.id,
        role="user",
        content="Did Site C pass the walkway check this week?",
        citations=[{"source_file": "HSE_Walkway_Policy.pdf", "page": 4}],
    )
    db_session.add(msg)
    db_session.flush()
    assert msg.session.id == session.id

    # 2. AgentRun & AgentToolCall
    agent_run = AgentRun(
        session_id=session.id,
        user_id=user.id,
        question="Did Site C pass the walkway check this week?",
        route="vision",
        total_tokens=650,
        estimated_cost_usd=0.0032,
        latency_ms=1840.5,
        status="success",
    )
    db_session.add(agent_run)
    db_session.flush()

    tool_call = AgentToolCall(
        agent_run_id=agent_run.id,
        tool_name="analyse_media",
        tool_args={"site_id": str(site.id), "time_window": "this_week"},
        tool_result={"detections_found": 3, "violations": 0},
        latency_ms=420.0,
    )
    db_session.add(tool_call)
    db_session.flush()
    assert tool_call.agent_run.id == agent_run.id

    # 3. Review (Capturing human correction with reviewer attribution)
    review = Review(
        item_type="extraction",
        item_id=uuid.uuid4(),
        inspection_id=inspection.id,
        original_value={"vendor": "Acme Supplires"},
        corrected_value={"vendor": "Acme Suppliers Ltd"},
        action="corrected",
        reviewer_id=reviewer.id,
        reviewer_notes="Corrected optical character recognition typo in vendor name",
    )
    db_session.add(review)
    db_session.flush()
    assert review.reviewer.id == reviewer.id
    assert review.action == "corrected"

    # 4. Ticket (Proposed by agent, requiring human approval)
    ticket = Ticket(
        finding_id=finding.id,
        inspection_id=inspection.id,
        title="Replace Expired Extinguisher",
        description="Fire extinguisher in Zone 1 is expired. Agent proposed immediate replacement ticket.",
        priority="high",
        status="proposed",
        proposed_by_agent=True,
    )
    db_session.add(ticket)
    db_session.flush()
    assert ticket.status == "proposed"
    assert ticket.proposed_by_agent is True

    # Human Approval Gate: Manager approves ticket
    ticket.status = "approved"
    ticket.approved_by = user.id
    ticket.approved_at = datetime.now(timezone.utc)
    db_session.flush()

    assert ticket.status == "approved"
    assert ticket.approver.id == user.id


def test_group_f_system_management(db_session: Session):
    """Verify Group F: reports, notifications, audit_logs."""
    user = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@sitesense.io",
        hashed_password="pw",
        full_name="Admin User",
        role="admin",
    )
    site = Site(name="Site D Construction", type="construction", location="Plot 4")
    db_session.add_all([user, site])
    db_session.flush()

    inspection = Inspection(site_id=site.id, status="completed")
    db_session.add(inspection)
    db_session.flush()

    # 1. Report (File path outside PostgreSQL)
    report = Report(
        inspection_id=inspection.id,
        format="pdf",
        file_path="/storage/reports/inspection_report_site_d.pdf",
        file_size_bytes=1420500,
        summary="Complete site audit report for Plot 4 with 12 detections and 1 minor finding.",
        generated_by=user.id,
    )
    db_session.add(report)
    db_session.flush()
    assert report.inspection.id == inspection.id

    # 2. Notification
    notification = Notification(
        user_id=user.id,
        title="New Ticket Awaiting Approval",
        message="Agent proposed a ticket for Site D inspection.",
        notification_type="ticket_approval",
        is_read=False,
    )
    db_session.add(notification)
    db_session.flush()
    assert notification.user.id == user.id

    # 3. AuditLog
    audit = AuditLog(
        user_id=user.id,
        action="approve_ticket",
        entity_type="ticket",
        entity_id=uuid.uuid4(),
        details={"approved_by": "Admin User", "priority": "high"},
        ip_address="192.168.1.100",
        user_agent="SiteSense-WebClient/1.0",
    )
    db_session.add(audit)
    db_session.flush()
    assert audit.user.id == user.id
    assert audit.action == "approve_ticket"
