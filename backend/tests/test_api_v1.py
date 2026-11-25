import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.computer_vision import Detection
from app.models.inspections_media import Inspection, Media
from app.models.knowledge_compliance import Finding, Rule
from app.models.users_sites import Site, SiteMembership, User


@pytest.fixture(scope="module")
def api_test_setup():
    """Seed test users, site, inspection, media, detection, rule, and finding."""
    session: Session = SessionLocal()
    default_pw = hash_password("SiteSense@2026")

    # 1. Users
    admin = User(name="API Admin", email="api_admin@sitesense.io", role="admin", password_hash=default_pw)
    manager = User(name="API Manager", email="api_manager@sitesense.io", role="manager", password_hash=default_pw)
    field_user = User(name="API Field", email="api_field@sitesense.io", role="field", password_hash=default_pw)
    session.add_all([admin, manager, field_user])
    session.flush()

    # 2. Site
    site = Site(name="API Test Depot", type="warehouse", location="Depot 42, North Wing")
    session.add(site)
    session.flush()

    # 3. Membership for field user
    membership = SiteMembership(user_id=field_user.id, site_id=site.id)
    session.add(membership)

    # 4. Rule
    rule = Rule(
        name="API Walkway Rule",
        description="Verify walkways are clear",
        rule_type="forbidden_object",
        parameters={"forbidden": ["pallet", "spill"]},
        policy_ref="Clause 4.1",
        severity="high",
    )
    session.add(rule)
    session.flush()

    # 5. Inspection
    inspection = Inspection(site_id=site.id, user_id=field_user.id, status="completed", summary="Weekly audit")
    session.add(inspection)
    session.flush()

    # 6. Media
    media = Media(
        inspection_id=inspection.id,
        type="image",
        path="/storage/test_img.jpg",
        filename="test_img.jpg",
    )
    session.add(media)
    session.flush()

    # 7. Detection
    detection = Detection(
        media_id=media.id,
        class_name="pallet",
        bbox=[50.0, 100.0, 200.0, 300.0],
        confidence=0.89,
        zone="Walkway A",
    )
    session.add(detection)
    session.flush()

    # 8. Finding
    finding = Finding(
        inspection_id=inspection.id,
        rule_id=rule.id,
        status="fail",
        evidence_ids=[str(detection.id)],
        reasoning="Pallet obstructing walkway in Zone A",
        severity="high",
    )
    session.add(finding)
    session.commit()

    context = {
        "admin_email": admin.email,
        "manager_email": manager.email,
        "field_email": field_user.email,
        "site_id": str(site.id),
        "inspection_id": str(inspection.id),
        "rule_id": str(rule.id),
        "finding_id": str(finding.id),
    }
    session.close()
    return context


def get_token(client: TestClient, email: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "SiteSense@2026"})
    return res.json()["token"]


def test_list_and_get_sites(client: TestClient, api_test_setup):
    """Verify GET /api/v1/sites and GET /api/v1/sites/{id}."""
    token = get_token(client, api_test_setup["admin_email"])
    headers = {"Authorization": f"Bearer {token}"}

    # List
    res = client.get("/api/v1/sites", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["total"] >= 1

    # Detail
    site_id = api_test_setup["site_id"]
    detail_res = client.get(f"/api/v1/sites/{site_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["name"] == "API Test Depot"
    assert "total_inspections" in detail


def test_create_site_rbac(client: TestClient, api_test_setup):
    """Verify only Admin can create sites; Field user is refused (403)."""
    admin_token = get_token(client, api_test_setup["admin_email"])
    field_token = get_token(client, api_test_setup["field_email"])

    new_site_payload = {
        "name": f"New Warehouse {uuid.uuid4().hex[:6]}",
        "type": "warehouse",
        "location": "Sector 9",
    }

    # Field user attempt -> 403
    res_field = client.post(
        "/api/v1/sites",
        json=new_site_payload,
        headers={"Authorization": f"Bearer {field_token}"},
    )
    assert res_field.status_code == 403

    # Admin attempt -> 201 Created
    res_admin = client.post(
        "/api/v1/sites",
        json=new_site_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin.status_code == 201
    assert res_admin.json()["name"] == new_site_payload["name"]


def test_inspections_crud_and_full_detail(client: TestClient, api_test_setup):
    """Verify full inspection detail contract:
    { inspection, media[], detections[], extractions[], findings[] }
    """
    field_token = get_token(client, api_test_setup["field_email"])
    headers = {"Authorization": f"Bearer {field_token}"}

    # 1. Create inspection
    create_res = client.post(
        "/api/v1/inspections",
        json={"site_id": api_test_setup["site_id"], "summary": "Morning Routine Inspection"},
        headers=headers,
    )
    assert create_res.status_code == 201
    created_id = create_res.json()["id"]

    # 2. List inspections
    list_res = client.get(f"/api/v1/inspections?site_id={api_test_setup['site_id']}", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 3. Get Full Inspection Detail (media + detections + extractions + findings)
    insp_id = api_test_setup["inspection_id"]
    detail_res = client.get(f"/api/v1/inspections/{insp_id}", headers=headers)
    assert detail_res.status_code == 200
    full_detail = detail_res.json()
    assert "inspection" in full_detail
    assert "media" in full_detail
    assert "detections" in full_detail
    assert "findings" in full_detail
    assert len(full_detail["media"]) >= 1
    assert len(full_detail["detections"]) >= 1
    assert len(full_detail["findings"]) >= 1
    assert full_detail["detections"][0]["class_name"] == "pallet"
    assert full_detail["findings"][0]["status"] == "fail"


def test_rules_endpoints(client: TestClient, api_test_setup):
    """Verify GET and POST /api/v1/rules."""
    admin_token = get_token(client, api_test_setup["admin_email"])
    mgr_token = get_token(client, api_test_setup["manager_email"])

    # 1. Manager lists rules
    list_res = client.get("/api/v1/rules", headers={"Authorization": f"Bearer {mgr_token}"})
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 2. Admin creates rule
    new_rule = {
        "name": f"Helmet Rule {uuid.uuid4().hex[:6]}",
        "description": "Hardhat mandatory beyond line",
        "rule_type": "required_object",
        "parameters": {"required_class": "safety_helmet"},
        "policy_ref": "Clause 2.4",
        "severity": "critical",
    }
    create_res = client.post(
        "/api/v1/rules",
        json=new_rule,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_res.status_code == 201
    assert create_res.json()["name"] == new_rule["name"]


def test_zones_endpoints(client: TestClient, api_test_setup):
    """Verify GET and POST /api/v1/zones."""
    admin_token = get_token(client, api_test_setup["admin_email"])
    headers = {"Authorization": f"Bearer {admin_token}"}
    site_id = api_test_setup["site_id"]

    # 1. Create zone
    zone_payload = {
        "site_id": site_id,
        "name": "Emergency Fire Exit Zone",
        "zone_type": "polygon",
        "coordinates": [[0, 0], [100, 0], [100, 100], [0, 100]],
        "applicable_classes": ["pallet", "debris"],
        "rules_config": {"clear_required": True},
    }
    create_res = client.post("/api/v1/zones", json=zone_payload, headers=headers)
    assert create_res.status_code == 201

    # 2. Retrieve site zones
    get_res = client.get(f"/api/v1/zones?site_id={site_id}", headers=headers)
    assert get_res.status_code == 200
    data = get_res.json()
    assert len(data["zones"]) >= 1
    assert data["zones"][0]["name"] == "Emergency Fire Exit Zone"


def test_tickets_creation_and_approval_workflow(client: TestClient, api_test_setup):
    """Verify Ticket creation and Manager approval gate."""
    mgr_token = get_token(client, api_test_setup["manager_email"])
    headers = {"Authorization": f"Bearer {mgr_token}"}
    finding_id = api_test_setup["finding_id"]

    # 1. Propose ticket (as if proposed by agent)
    ticket_payload = {
        "finding_id": finding_id,
        "title": "Clear Blocked Walkway",
        "description": "Pallet must be moved immediately to clear emergency exit path.",
        "priority": "high",
        "proposed_by_agent": True,
    }
    create_res = client.post("/api/v1/tickets", json=ticket_payload, headers=headers)
    assert create_res.status_code == 201
    ticket = create_res.json()
    assert ticket["status"] == "proposed"
    ticket_id = ticket["id"]

    # 2. Manager approves ticket
    approve_res = client.post(
        f"/api/v1/tickets/{ticket_id}/approve",
        json={"approved": True, "resolution_notes": "Assigned to shift supervisor for immediate relocation."},
        headers=headers,
    )
    assert approve_res.status_code == 200
    approved_ticket = approve_res.json()
    assert approved_ticket["status"] == "approved"
    assert approved_ticket["approved_by"] is not None
    assert approved_ticket["approved_at"] is not None

    # 3. List tickets
    list_res = client.get(f"/api/v1/tickets?finding_id={finding_id}", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1
