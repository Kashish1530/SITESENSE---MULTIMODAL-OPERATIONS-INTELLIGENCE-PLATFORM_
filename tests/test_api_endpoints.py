"""
tests/test_api_endpoints.py
Unit tests for FastAPI endpoints in api_service.py.
"""
import pytest
import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from api_service import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RUNNING"
    assert "db_stats" in data

def test_violations_endpoints():
    # 1. Active violations
    r_act = client.get("/vision/violations/active")
    assert r_act.status_code == 200
    assert "violations" in r_act.json()

    # 2. Resolved violations
    r_res = client.get("/vision/violations/resolved")
    assert r_res.status_code == 200
    assert "violations" in r_res.json()

    # 3. Weekly summary
    r_sum = client.get("/vision/violations/weekly-summary")
    assert r_sum.status_code == 200
    assert "weekly_summary" in r_sum.json()

def test_dynamic_zone_endpoints():
    # 1. Fetch schema
    r_schema = client.get("/vision/zones/schema")
    assert r_schema.status_code == 200
    assert r_schema.json()["title"] == "SiteSenseZoneConfig"

    # 2. Fetch zones for site
    r_get = client.get("/vision/zones/warehouse")
    assert r_get.status_code == 200
    data = r_get.json()
    assert "zones" in data
    assert "emergency_exit" in data["zones"]

    # 3. Dry-run validation endpoint
    payload = {
        "site_id": "TEST_SITE_DYNAMIC",
        "camera_id": "CAM_TEST_01",
        "zones": {
            "danger_zone": {
                "zone_id": "ZONE_DANGER_99",
                "zone_name": "Crane Danger Zone",
                "zone_type": "exclusion",
                "alert_severity": "CRITICAL",
                "coordinates": [[100, 100], [400, 100], [400, 400], [100, 400]],
                "prohibited_classes": [0],
                "blockage_threshold_seconds": 2.0,
                "description": "Dynamic zone created by admin"
            }
        }
    }
    r_val = client.post("/vision/zones/validate", json=payload)
    assert r_val.status_code == 200
    assert r_val.json()["valid"] is True

    # 4. Update dynamic zones (Screen 12 - M6.9)
    r_post = client.post("/vision/zones/TEST_SITE_DYNAMIC", json=payload)
    assert r_post.status_code == 200
    assert r_post.json()["status"] in ["SUCCESS", "UPDATED"]

    # 5. Verify retrieved updated zone
    r_verify = client.get("/vision/zones/TEST_SITE_DYNAMIC")
    assert r_verify.status_code == 200
    assert "danger_zone" in r_verify.json()["zones"]

    # 6. Rejection of invalid zone geometry (400 Bad Request)
    invalid_payload = {
        "site_id": "TEST_FAIL",
        "camera_id": "CAM_FAIL",
        "zones": {
            "broken_zone": {
                "zone_id": "Z_BROKEN",
                "zone_name": "Broken Zone",
                "coordinates": [[100, 100]],  # Only 1 point!
                "alert_severity": "CRITICAL"
            }
        }
    }
    r_fail = client.post("/vision/zones/TEST_FAIL", json=invalid_payload)
    assert r_fail.status_code == 400
    assert "VALIDATION_FAILED" in str(r_fail.json())

