"""
tests/test_violation_db.py
Unit tests for SiteSense Violation Lifecycle Database.
"""
import pytest
import os
import sys

sys.path.append(os.path.abspath("src"))
from violation_db import (
    init_db,
    insert_violation,
    resolve_violation,
    get_active_violations,
    get_resolved_violations,
    get_violation_by_id,
    get_weekly_summary,
    get_all_violations_count
)

def test_db_lifecycle():
    init_db()

    # 1. Mock Event
    mock_event = {
        "event_id": "EVT_TEST_001",
        "site_id": "SITE_TEST",
        "zone_id": "zone_exit_test",
        "zone_name": "Emergency Fire Exit Door",
        "event_type": "EMERGENCY_EXIT_BLOCKED",
        "severity": "CRITICAL",
        "target": {
            "track_id": 999,
            "class_name": "pallet",
            "class_id": 5
        },
        "temporal": {
            "dwell_time_seconds": 7.5,
            "current_timestamp": 12.0
        }
    }

    # 2. Insert Violation
    v_id = insert_violation(mock_event, evidence_path="outputs/evidence_frames/test.jpg", video_name="test.mp4")
    assert v_id is not None
    assert len(v_id) > 10

    # Verify Active
    active = get_active_violations(site_id="SITE_TEST")
    matching = [v for v in active if v["id"] == v_id]
    assert len(matching) == 1
    assert matching[0]["severity"] == "CRITICAL"
    assert matching[0]["class_name"] == "pallet"
    assert matching[0]["status"] == "ACTIVE"

    # 3. Resolve Violation with proof
    res_success = resolve_violation(
        violation_id=v_id,
        resolved_by="safety_officer_amit",
        resolution_photo_path="outputs/resolution_proofs/test_proof.jpg",
        resolution_note="Pallet moved to racking aisle 4. Exit door fully clear."
    )
    assert res_success is True

    # 4. Verify Not Active anymore
    active_after = get_active_violations(site_id="SITE_TEST")
    matching_after = [v for v in active_after if v["id"] == v_id]
    assert len(matching_after) == 0

    # 5. Verify In Resolved List
    resolved = get_resolved_violations(site_id="SITE_TEST")
    matching_resolved = [v for v in resolved if v["id"] == v_id]
    assert len(matching_resolved) == 1
    assert matching_resolved[0]["status"] == "RESOLVED"
    assert matching_resolved[0]["resolved_by"] == "safety_officer_amit"
    assert "Pallet moved" in matching_resolved[0]["resolution_note"]
    assert matching_resolved[0]["resolution_photo_path"] == "outputs/resolution_proofs/test_proof.jpg"

    # 6. Verify get_violation_by_id
    detail = get_violation_by_id(v_id)
    assert detail is not None
    assert detail["id"] == v_id
    assert detail["resolved_by"] == "safety_officer_amit"

    # 7. Verify Weekly Summary
    summary = get_weekly_summary(site_id="SITE_TEST")
    assert len(summary) >= 1
    assert summary[0]["resolved"] >= 1
