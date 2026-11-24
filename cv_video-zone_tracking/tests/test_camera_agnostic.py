"""
tests/test_camera_agnostic.py
Unit tests verifying Feature 2.4 Deliverable 5:
"Camera-Agnostic Zone Configuration: Zones defined in config work on a camera angle the team did not tune for without code changes."
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from zone_engine import ZoneEngine

def test_load_all_camera_configs_without_code_changes():
    configs = [
        "config/camera_001.json",
        "config/camera_002.json",
        "config/camera_003_unseen.json"
    ]
    
    for cfg_path in configs:
        assert os.path.exists(cfg_path), f"Config file missing: {cfg_path}"
        engine = ZoneEngine(cfg_path)
        assert len(engine.zones) >= 2, f"Expected at least 2 zones in {cfg_path}"
        assert engine.config["camera_id"] is not None

def test_unseen_camera_angle_zone_and_line_evaluation():
    # Load completely unseen camera angle configuration
    engine = ZoneEngine("config/camera_003_unseen.json")
    assert engine.config["camera_id"] == "CAM_003_UNSEEN"
    
    # 1. Object inside high_rack_loading_dock zone (coords: [950, 350] to [1750, 950])
    # Pallet (class 5) at x=1200, y=600 (ground point: 1200, 600)
    tracked_pallet = [{
        "track_id": 999,
        "class_id": 5,
        "confidence": 0.94,
        "bbox": [1150, 500, 1250, 600]
    }]
    
    # At t = 10s: entry
    violations, crossings = engine.evaluate_tracks(tracked_pallet, timestamp=10.0)
    assert len(violations) == 0  # < 3.0s threshold
    
    # At t = 13.5s: dwell threshold exceeded (> 3.0s)
    violations, crossings = engine.evaluate_tracks(tracked_pallet, timestamp=13.5)
    assert len(violations) == 1
    assert violations[0]["zone_id"] == "ZONE_DOCK_EAST_01"
    assert violations[0]["dwell_time_seconds"] == 3.5

    # 2. Line crossing on unseen camera: vehicle (class 12) crosses dock_portal_flow at y=650
    # From y=600 to y=700
    v_t1 = [{"track_id": 888, "class_id": 12, "bbox": [1200, 550, 1400, 600]}] # ground y=600
    v_t2 = [{"track_id": 888, "class_id": 12, "bbox": [1200, 650, 1400, 700]}] # ground y=700
    
    engine.evaluate_tracks(v_t1, timestamp=15.0)
    _, crossings = engine.evaluate_tracks(v_t2, timestamp=16.0)
    assert len(crossings) == 1
    assert crossings[0]["line_id"] == "LINE_PORTAL_01"
