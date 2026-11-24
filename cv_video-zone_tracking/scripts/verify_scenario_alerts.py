"""
scripts/verify_scenario_alerts.py
Simulates and verifies zone tracking and emergency exit blockage detection
against the generated 5-minute demo videos and mock detection streams.
"""
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from zone_engine import ZoneEngine
from event_generator import SpatialEventFormatter

def verify_video_scenario(video_name, meta_json, zone_json, site_id):
    print(f"\n======================================================================")
    print(f"[*] Verifying Scenario & Zone Tracking: {video_name}")
    print(f"[*] Metadata: {meta_json} | Config: {zone_json}")
    print(f"======================================================================")
    
    with open(meta_json, "r") as f:
        detections_feed = json.load(f)
        
    engine = ZoneEngine(zone_json)
    emitted_alerts = []
    
    sorted_frames = sorted([int(k) for k in detections_feed.keys()])
    
    for f_idx in sorted_frames:
        frame_data = detections_feed[str(f_idx)]
        timestamp = frame_data["timestamp"]
        
        # Prepare tracked objects
        tracked_objects = []
        for det_idx, det in enumerate(frame_data["detections"]):
            c_id, x1, y1, x2, y2, conf = det
            # Stable track ID based on class + coarse grid for test feed
            t_id = 1000 + c_id * 50 + (x1 // 150)
            tracked_objects.append({
                "track_id": t_id,
                "class_id": c_id,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2]
            })
            
        violations, crossings = engine.evaluate_tracks(tracked_objects, timestamp)
        for viol in violations:
            event = SpatialEventFormatter.format_event(viol, site_id=site_id, camera_id=engine.config.get("camera_id", "CAM_01"))
            emitted_alerts.append(event)
            
    print(f"[+] Total Evaluation Timepoints: {len(sorted_frames)}")
    print(f"[+] Total Alert Violations Emitted: {len(emitted_alerts)}")
    
    # Group by event type
    by_type = {}
    for ev in emitted_alerts:
        et = ev["event_type"]
        by_type[et] = by_type.get(et, 0) + 1
        
    print(f"[+] Alert Breakdown:")
    for et, count in by_type.items():
        print(f"    - {et}: {count} occurrences")
        
    # Sample first alert
    if emitted_alerts:
        sample = emitted_alerts[0]
        print(f"\n[+] Sample Triggered Event:")
        print(f"    Event ID: {sample['event_id']}")
        print(f"    Type: {sample['event_type']} ({sample['severity']})")
        print(f"    Zone: {sample['zone_name']}")
        print(f"    Target: {sample['target']['class_name']} (Class {sample['target']['class_id']})")
        print(f"    Dwell Time: {sample['temporal']['dwell_time_seconds']}s")
        print(f"    Action: {sample['recommended_action']}")

if __name__ == "__main__":
    verify_video_scenario(
        "Construction Site (5 Min)",
        "data/mock_detections_construction.json",
        "config/zones_config_construction.json",
        "SITE_CONST_01"
    )
    
    verify_video_scenario(
        "Warehouse Operations (5 Min)",
        "data/mock_detections_warehouse.json",
        "config/zones_config_warehouse.json",
        "SITE_WH_01"
    )

