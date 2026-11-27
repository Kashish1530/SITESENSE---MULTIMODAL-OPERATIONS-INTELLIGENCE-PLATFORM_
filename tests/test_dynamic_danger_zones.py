"""
tests/test_dynamic_danger_zones.py
Unit tests for Dynamic Machinery Circular Danger Zones (OSHA Proximity Buffers):
- Moving circular danger halo centered at heavy machinery ground base.
- Pixel distance calculation between workers and machinery.
- High-priority danger alerts emitted when distance <= danger_radius_px.
- Zero false alarms for workers outside the danger buffer.
"""

import sys
import os
import json
import tempfile
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from zone_engine import ZoneEngine
from annotator import VisualAnnotator
from event_generator import SpatialEventFormatter


def test_machinery_circular_danger_zone_detection():
    # Setup test config with dynamic_danger_zones enabled
    config_dict = {
        "camera_id": "TEST_CAM_DANGER",
        "zones": {},
        "counting_lines": {},
        "dynamic_danger_zones": {
            "enabled": True,
            "machinery_classes": [11, 12, 14],  # forklift, vehicle, machinery
            "target_classes": [0],             # person
            "danger_radius_px": 180.0,
            "warning_radius_px": 260.0,
            "alert_severity": "CRITICAL"
        }
    }

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
        json.dump(config_dict, f)
        cfg_path = f.name

    try:
        engine = ZoneEngine(cfg_path)
        assert engine.dynamic_danger_config["enabled"] is True
        assert engine.dynamic_danger_config["danger_radius_px"] == 180.0

        # Frame 1: Forklift (ID 10) at ground base (500, 600)
        # Person 1 (ID 1) at ground base (540, 620) -> dist = sqrt(40^2 + 20^2) = 44.7px (< 180px) -> DANGER!
        # Person 2 (ID 2) at ground base (850, 950) -> dist = sqrt(350^2 + 350^2) = 494.9px (> 180px) -> SAFE
        tracked_objects = [
            {
                "track_id": 10,
                "class_id": 11,
                "class_name": "forklift",
                "confidence": 0.95,
                "bbox": [400, 400, 600, 600]  # base center: (500, 600)
            },
            {
                "track_id": 1,
                "class_id": 0,
                "class_name": "person",
                "confidence": 0.92,
                "bbox": [520, 500, 560, 620]  # base center: (540, 620)
            },
            {
                "track_id": 2,
                "class_id": 0,
                "class_name": "person",
                "confidence": 0.88,
                "bbox": [820, 800, 880, 950]  # base center: (850, 950)
            }
        ]

        violations, crossings = engine.evaluate_tracks(tracked_objects, timestamp=5.0)

        # Person 1 must trigger CRITICAL danger violation
        assert len(violations) == 1, f"Expected 1 proximity violation, got: {len(violations)}"
        v = violations[0]
        assert v["zone_type"] == "dynamic_danger_zone"
        assert v["severity"] == "CRITICAL"
        assert v["person_id"] == 1
        assert v["machine_id"] == 10
        assert v["machine_class"] == "forklift"
        assert v["distance_px"] < 50.0
        assert v["danger_radius_px"] == 180.0

        # Verify dynamic danger circle metadata
        assert len(engine.last_dynamic_danger_circles) == 1
        circle = engine.last_dynamic_danger_circles[0]
        assert circle["machine_id"] == 10
        assert circle["is_violated"] is True
        assert circle["radius"] == 180

        # Event formatting verification
        event = SpatialEventFormatter.format_event(v, site_id="SITE_TEST", camera_id="CAM_TEST")
        assert event["event_type"] == "MACHINERY_PROXIMITY_HAZARD"
        assert event["target"]["person_id"] == 1
        assert event["target"]["machine_id"] == 10
        assert "step back immediately" in event["recommended_action"]

    finally:
        if os.path.exists(cfg_path):
            os.remove(cfg_path)


def test_dynamic_danger_zone_clearance():
    # When person moves outside radius, violation clears
    config_dict = {
        "camera_id": "TEST_CAM_CLEAR",
        "zones": {},
        "dynamic_danger_zones": {
            "enabled": True,
            "machinery_classes": [11],
            "target_classes": [0],
            "danger_radius_px": 100.0,
            "alert_severity": "CRITICAL"
        }
    }
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
        json.dump(config_dict, f)
        cfg_path = f.name

    try:
        engine = ZoneEngine(cfg_path)
        # Person is 150px away from machine -> no violation
        tracked_objects = [
            {"track_id": 99, "class_id": 11, "class_name": "forklift", "bbox": [200, 200, 400, 400]},
            {"track_id": 7, "class_id": 0, "class_name": "person", "bbox": [450, 200, 500, 400]}  # dx = 175px > 100px
        ]
        violations, _ = engine.evaluate_tracks(tracked_objects, timestamp=2.0)
        assert len(violations) == 0
        assert engine.last_dynamic_danger_circles[0]["is_violated"] is False
    finally:
        if os.path.exists(cfg_path):
            os.remove(cfg_path)


def test_visual_annotator_dynamic_danger_zones():
    # Frame shape: 720x1280
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    dynamic_circles = [{
        "machine_id": 5,
        "class_id": 11,
        "class_name": "forklift",
        "center": (640, 360),
        "radius": 150,
        "warning_radius": 220,
        "is_violated": True
    }]
    proximity_alerts = [{
        "person_pt": (680, 390),
        "machine_pt": (640, 360),
        "distance_px": 50.0,
        "danger_radius_px": 150.0,
        "person_id": 12,
        "machine_id": 5,
        "machine_class": "forklift"
    }]

    annotated = VisualAnnotator.draw_dynamic_danger_zones(frame, dynamic_circles, proximity_alerts)
    assert annotated is not None
    assert annotated.shape == (720, 1280, 3)
