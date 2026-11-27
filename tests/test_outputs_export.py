"""
tests/test_outputs_export.py
Unit tests verifying the 3 standardized output formats for Member 3 (GenAI & Agentic AI):
- Output A: tracking_results.csv
- Output B: zone_events.csv
- Output C: zone_summary.json
"""

import os
import sys
import json
import csv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from tracking_metrics import TrackingMetricsTracker
from zone_engine import ZoneEngine

def test_standardized_outputs_for_member3(tmp_path):
    tracker_metrics = TrackingMetricsTracker(site_id="SITE_TEST_A", camera_id="CAM_TEST_01")
    
    # Mock tracking detections
    mock_objs = [{
        "track_id": 12,
        "class_id": 0,
        "confidence": 0.92,
        "bbox": [100, 200, 150, 350]
    }]
    tracker_metrics.add_tracking_detections(frame_idx=100, timestamp=3.33, tracked_objects=mock_objs, class_names={0: "person"})
    
    # Mock zone violation
    mock_viols = [{
        "track_id": 12,
        "zone_id": "ZONE_01",
        "zone_name": "Restricted Area",
        "status": "ACTIVE_VIOLATION",
        "dwell_time_seconds": 25.5,
        "severity": "CRITICAL"
    }]
    tracker_metrics.add_zone_events(mock_viols, timestamp=3.33)
    
    # Output paths
    csv_a = str(tmp_path / "tracking_results.csv")
    csv_b = str(tmp_path / "zone_events.csv")
    json_c = str(tmp_path / "zone_summary.json")
    
    # 1. Test Output A
    tracker_metrics.export_output_a_tracking_results(csv_a)
    assert os.path.exists(csv_a)
    with open(csv_a, "r") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 1
        assert reader[0]["track_id"] == "12"
        assert reader[0]["class_name"] == "person"
        assert float(reader[0]["confidence"]) == 0.92
        assert float(reader[0]["timestamp"]) == 3.33
        
    # 2. Test Output B
    tracker_metrics.export_output_b_zone_events(csv_b)
    assert os.path.exists(csv_b)
    with open(csv_b, "r") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 1
        assert reader[0]["zone_name"] == "Restricted Area"
        assert reader[0]["severity"] == "CRITICAL"
        assert float(reader[0]["dwell_time"]) == 25.5

    # 3. Test Output C
    engine = ZoneEngine("config/camera_001.json")
    tracker_metrics.export_output_c_zone_summary(json_c, unique_person_count=1, zone_engine=engine, counting_lines=engine.counting_lines)
    assert os.path.exists(json_c)
    with open(json_c, "r") as f:
        summary_data = json.load(f)
        assert summary_data["site_id"] == "SITE_TEST_A"
        assert summary_data["unique_person_count"] == 1
        assert "zones" in summary_data
        assert len(summary_data["zones"]) >= 1
