import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.models.inspections_media import Inspection
from app.models.knowledge_compliance import Finding, Rule
from app.models.users_sites import Site, SiteMembership, User


@pytest.fixture(scope="module")
def full_api_setup():
    """Setup test users, site, and inspection for full API testing."""
    session: Session = SessionLocal()
    default_pw = hash_password("SiteSense@2026")

    suffix = uuid.uuid4().hex[:6]
    # Users
    admin = User(name="Admin Coverage", email=f"cov_admin_{suffix}@sitesense.io", role="admin", password_hash=default_pw)
    manager = User(name="Manager Coverage", email=f"cov_mgr_{suffix}@sitesense.io", role="manager", password_hash=default_pw)
    field_user = User(name="Field Coverage", email=f"cov_fld_{suffix}@sitesense.io", role="field", password_hash=default_pw)
    reviewer = User(name="Reviewer Coverage", email=f"cov_rev_{suffix}@sitesense.io", role="reviewer", password_hash=default_pw)
    session.add_all([admin, manager, field_user, reviewer])
    session.flush()

    # Site
    site = Site(name="Coverage Warehouse", type="warehouse", location="Depot 99")
    session.add(site)
    session.flush()

    # Membership
    session.add(SiteMembership(user_id=field_user.id, site_id=site.id))
    session.add(SiteMembership(user_id=reviewer.id, site_id=site.id))

    # Rule
    rule = Rule(
        name=f"Coverage Rule {suffix}",
        description="Verify PPE is worn",
        rule_type="required_object",
        parameters={"required": ["vest", "helmet"]},
        policy_ref="Clause 3.1",
        severity="medium",
    )
    session.add(rule)
    session.flush()

    # Inspection
    inspection = Inspection(site_id=site.id, user_id=field_user.id, status="completed", summary="Coverage audit")
    session.add(inspection)
    session.flush()

    # Pending Finding for Review Queue
    finding = Finding(
        inspection_id=inspection.id,
        rule_id=rule.id,
        status="review",
        evidence_ids=["evd-101"],
        reasoning="Uncertain whether helmet is fastened",
        severity="medium",
    )
    session.add(finding)
    session.commit()

    tokens = {
        "admin": create_access_token(admin.id, admin.email, admin.role),
        "manager": create_access_token(manager.id, manager.email, manager.role),
        "field": create_access_token(field_user.id, field_user.email, field_user.role),
        "reviewer": create_access_token(reviewer.id, reviewer.email, reviewer.role),
    }

    data = {
        "admin": admin,
        "manager": manager,
        "field": field_user,
        "reviewer": reviewer,
        "site": site,
        "rule": rule,
        "inspection": inspection,
        "finding": finding,
        "tokens": tokens,
    }
    yield data
    session.close()


def test_jobs_api_lifecycle(client: TestClient, full_api_setup):
    """Test POST /jobs, GET /jobs/{id}, and GET /jobs."""
    headers = {"Authorization": f"Bearer {full_api_setup['tokens']['field']}"}

    # 1. Enqueue job
    create_res = client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "inspection_id": str(full_api_setup["inspection"].id),
            "job_type": "inspection_ingestion",
        },
    )
    assert create_res.status_code == 201
    job_data = create_res.json()
    assert job_data["status"] == "queued"
    assert job_data["progress"] == 0
    job_id = job_data["id"]

    # 2. Get job status
    get_res = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == job_id
    assert get_res.json()["current_stage"] == "queued_for_worker"

    # 3. List jobs
    list_res = client.get("/api/v1/jobs", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1


def test_findings_api_lifecycle(client: TestClient, full_api_setup):
    """Test POST, GET, and PATCH /findings."""
    field_headers = {"Authorization": f"Bearer {full_api_setup['tokens']['field']}"}
    manager_headers = {"Authorization": f"Bearer {full_api_setup['tokens']['manager']}"}

    # 1. Create finding
    create_res = client.post(
        "/api/v1/findings",
        headers=field_headers,
        json={
            "inspection_id": str(full_api_setup["inspection"].id),
            "rule_id": str(full_api_setup["rule"].id),
            "status": "fail",
            "evidence_ids": ["evd-001", "evd-002"],
            "reasoning": "Missing safety helmet in loading dock",
            "severity": "high",
        },
    )
    assert create_res.status_code == 201
    f_data = create_res.json()
    assert f_data["status"] == "fail"
    finding_id = f_data["id"]

    # 2. Get finding detail
    get_res = client.get(f"/api/v1/findings/{finding_id}", headers=field_headers)
    assert get_res.status_code == 200
    assert get_res.json()["severity"] == "high"

    # 3. List findings
    list_res = client.get(
        f"/api/v1/findings?inspection_id={full_api_setup['inspection'].id}&severity=high",
        headers=field_headers,
    )
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 4. Patch finding (Manager role)
    patch_res = client.patch(
        f"/api/v1/findings/{finding_id}",
        headers=manager_headers,
        json={"status": "pass", "reasoning": "Corrected on reinspection: employee wore helmet"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "pass"


def test_chat_api_lifecycle(client: TestClient, full_api_setup):
    """Test POST /chat/sessions, POST /chat/sessions/{id}/messages, GET /chat/sessions."""
    headers = {"Authorization": f"Bearer {full_api_setup['tokens']['field']}"}

    # 1. Create chat session
    session_res = client.post(
        "/api/v1/chat/sessions",
        headers=headers,
        json={"title": "PPE Query", "site_id": str(full_api_setup["site"].id)},
    )
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    # 2. Send message
    msg_res = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=headers,
        json={"content": "What are the rules regarding walkway clearance and pallets?"},
    )
    assert msg_res.status_code == 201
    query_data = msg_res.json()
    assert query_data["route"] in ("policy", "multimodal")
    assert len(query_data["citations"]) > 0
    assert "Clause 4.2" in query_data["citations"][0]["clause"]
    assert query_data["assistant_message"]["role"] == "assistant"

    # 3. Get message history
    history_res = client.get(f"/api/v1/chat/sessions/{session_id}/messages", headers=headers)
    assert history_res.status_code == 200
    assert history_res.json()["total"] == 2  # user + assistant

    # 4. List sessions
    list_sessions = client.get("/api/v1/chat/sessions", headers=headers)
    assert list_sessions.status_code == 200
    assert list_sessions.json()["total"] >= 1


def test_review_queue_and_action(client: TestClient, full_api_setup):
    """Test GET /reviews/queue, POST /reviews, and GET /reviews/history."""
    reviewer_headers = {"Authorization": f"Bearer {full_api_setup['tokens']['reviewer']}"}

    # 1. Fetch review queue (should contain the finding created with status="review")
    queue_res = client.get("/api/v1/reviews/queue", headers=reviewer_headers)
    assert queue_res.status_code == 200
    queue_items = queue_res.json()["items"]
    assert len(queue_items) >= 1

    # Find the target finding queue item
    target = next((item for item in queue_items if item["item_type"] == "finding"), None)
    assert target is not None

    # 2. Submit review action
    review_res = client.post(
        "/api/v1/reviews",
        headers=reviewer_headers,
        json={
            "item_type": "finding",
            "item_id": target["id"],
            "inspection_id": target["inspection_id"],
            "action": "accepted",
            "reviewer_notes": "Verified by human reviewer: conditions acceptable",
        },
    )
    assert review_res.status_code == 201
    assert review_res.json()["action"] == "accepted"

    # 3. Check history
    history_res = client.get("/api/v1/reviews/history", headers=reviewer_headers)
    assert history_res.status_code == 200
    assert history_res.json()["total"] >= 1


def test_reports_api_lifecycle(client: TestClient, full_api_setup):
    """Test POST /reports/generate, GET /reports, and GET /reports/{id}."""
    manager_headers = {"Authorization": f"Bearer {full_api_setup['tokens']['manager']}"}

    # 1. Generate report
    gen_res = client.post(
        "/api/v1/reports/generate",
        headers=manager_headers,
        json={
            "inspection_id": str(full_api_setup["inspection"].id),
            "format": "json",
            "summary": "Full warehouse compliance inspection completed successfully.",
        },
    )
    assert gen_res.status_code == 201
    rep_data = gen_res.json()
    assert rep_data["format"] == "json"
    report_id = rep_data["id"]

    # 2. Get report metadata
    get_res = client.get(f"/api/v1/reports/{report_id}", headers=manager_headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == report_id

    # 3. Download report file
    dl_res = client.get(f"/api/v1/reports/{report_id}/download", headers=manager_headers)
    assert dl_res.status_code == 200
    assert "report_id" in dl_res.json()

    # 4. List reports
    list_res = client.get("/api/v1/reports", headers=manager_headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1


def test_admin_api_lifecycle(client: TestClient, full_api_setup):
    """Test admin endpoints: users, audit logs, and stats."""
    admin_headers = {"Authorization": f"Bearer {full_api_setup['tokens']['admin']}"}
    field_headers = {"Authorization": f"Bearer {full_api_setup['tokens']['field']}"}

    # 1. Non-admin forbidden from admin endpoints
    forbidden_res = client.get("/api/v1/admin/users", headers=field_headers)
    assert forbidden_res.status_code == 403
    assert forbidden_res.json()["error"]["code"] == "FORBIDDEN"

    # 2. List users
    users_res = client.get("/api/v1/admin/users", headers=admin_headers)
    assert users_res.status_code == 200
    assert users_res.json()["total"] >= 4

    # 3. Create user
    new_email = f"new_operator_{uuid.uuid4().hex[:6]}@sitesense.io"
    create_res = client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "name": "New Safety Operator",
            "email": new_email,
            "password": "SiteSense@2026",
            "role": "field",
            "site_id": str(full_api_setup["site"].id),
        },
    )
    assert create_res.status_code == 201
    created_user_id = create_res.json()["id"]

    # 4. Update user
    patch_res = client.patch(
        f"/api/v1/admin/users/{created_user_id}",
        headers=admin_headers,
        json={"role": "manager", "name": "Promoted Safety Manager"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["role"] == "manager"

    # 5. Audit logs
    audit_res = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert audit_res.status_code == 200
    assert audit_res.json()["total"] >= 1

    # 6. Stats
    stats_res = client.get("/api/v1/admin/stats", headers=admin_headers)
    assert stats_res.status_code == 200
    assert stats_res.json()["total_users"] >= 5


def test_consistent_error_shapes_across_codes(client: TestClient, full_api_setup):
    """Verify that all error responses follow { "error": { "code": str, "message": str, "detail": Any } }."""
    headers = {"Authorization": f"Bearer {full_api_setup['tokens']['field']}"}

    # 404 Not Found
    res_404 = client.get(f"/api/v1/jobs/{uuid.uuid4()}", headers=headers)
    assert res_404.status_code == 404
    data_404 = res_404.json()
    assert "error" in data_404
    assert data_404["error"]["code"] == "NOT_FOUND"
    assert isinstance(data_404["error"]["message"], str)

    # 401 Unauthorized (missing or bad token)
    res_401 = client.get("/api/v1/jobs")
    assert res_401.status_code == 401
    data_401 = res_401.json()
    assert "error" in data_401
    assert data_401["error"]["code"] == "UNAUTHORIZED"

    # 403 Forbidden
    res_403 = client.get("/api/v1/admin/users", headers=headers)
    assert res_403.status_code == 403
    data_403 = res_403.json()
    assert "error" in data_403
    assert data_403["error"]["code"] == "FORBIDDEN"

    # 422 Validation Error
    res_422 = client.post("/api/v1/jobs", headers=headers, json={"job_type": 12345})
    assert res_422.status_code == 422
    data_422 = res_422.json()
    assert "error" in data_422
    assert data_422["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(data_422["error"]["detail"], list)
