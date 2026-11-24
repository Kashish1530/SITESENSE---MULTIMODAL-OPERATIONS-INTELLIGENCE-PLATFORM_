"""
tests/test_dwell_timer.py
Unit tests for blockage duration thresholds and debounce persistence.
"""
import sys
import os
import tempfile
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from zone_engine import ZoneEngine

def test_dwell_timer_threshold_and_clearance():
    # Mock config with 4.0s threshold
    config_dict = {
        "camera_id": "TEST_CAM",
        "zones": {
            "emergency_exit": {
                "zone_id": "ZONE_EXIT_01",
                "zone_name": "Test Exit",
                "zone_type": "exclusion",
                "alert_severity": "CRITICAL",
                "coordinates": [[800, 500], [1400, 500], [1400, 1080], [800, 1080]],
                "prohibited_classes": [5, 11, 13],
                "blockage_threshold_seconds": 4.0,
                "description": "Evacuation path must have zero obstruction"
            }
        }
    }
    
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
        json.dump(config_dict, f)
        cfg_path = f.name
        
    try:
        engine = ZoneEngine(cfg_path)
        
        # Pallet (class 5) at x=900, y=700 (inside exit zone)
        tracked_obj = [{
            "track_id": 101,
            "class_id": 5,
            "confidence": 0.95,
            "bbox": [900, 600, 1100, 800] # bottom center = (1000, 800) -> inside!
        }]
        
        # Frame at t = 10.0s (Entry)
        violations, _ = engine.evaluate_tracks(tracked_obj, timestamp=10.0)
        assert len(violations) == 0  # 0.0s < 4.0s threshold
        
        # Frame at t = 13.0s (3.0s dwell)
        violations, _ = engine.evaluate_tracks(tracked_obj, timestamp=13.0)
        assert len(violations) == 0  # 3.0s < 4.0s threshold
        
        # Frame at t = 14.5s (4.5s dwell) -> Violation emitted!
        violations, _ = engine.evaluate_tracks(tracked_obj, timestamp=14.5)
        assert len(violations) == 1
        assert violations[0]["zone_id"] == "ZONE_EXIT_01"
        assert violations[0]["dwell_time_seconds"] == 4.5
        assert violations[0]["status"] == "ACTIVE_VIOLATION"
        
        # Object removed at t = 16.0s
        violations, _ = engine.evaluate_tracks([], timestamp=16.0)
        assert len(violations) == 0
        # Dwell tracker cleared
        assert (101, "emergency_exit") not in engine.dwell_tracker
    finally:
        if os.path.exists(cfg_path):
            os.remove(cfg_path)

