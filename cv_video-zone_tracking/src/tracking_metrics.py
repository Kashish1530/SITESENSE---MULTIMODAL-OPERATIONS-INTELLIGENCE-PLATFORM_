"""
tracking_metrics.py
SiteSense Feature 2.3 & 2.4 — Evaluation Metrics, ID Switch Analysis & Output Exporter

Responsibilities:
- Record per-frame tracking records for downstream export to Member 3.
- Compute tracking metrics: FPS, latency per frame, unique counts, ID switches.
- Export Output A: tracking_results.csv (frame, timestamp, track_id, class, confidence, bbox)
- Export Output B: zone_events.csv (track_id, zone_id, zone_name, event, timestamp, dwell_time)
- Export Output C: zone_summary.json (site_id, camera_id, unique_person_count, entries, exits, zones)
"""

import os
import csv
import json
import time
from typing import List, Dict, Any, Optional

class TrackingMetricsTracker:
    def __init__(self, site_id: str = "SITE_01", camera_id: str = "CAM_01"):
        self.site_id = site_id
        self.camera_id = camera_id
        
        # Performance timing
        self.frame_latencies: List[float] = []
        self.start_wall_time = time.time()
        
        # Raw records for Output A
        self.tracking_records: List[Dict[str, Any]] = []
        
        # Zone event records for Output B
        self.zone_event_records: List[Dict[str, Any]] = []
        
        # ID-switch heuristic tracking: maps spatial centroids to recent track IDs
        self.centroid_to_last_track: Dict[int, Any] = {}
        self.id_switch_count: int = 0

    def record_frame_start(self) -> float:
        """Marks the start timestamp for latency calculation."""
        return time.perf_counter()

    def record_frame_end(self, start_t: float):
        """Records latency for a single frame."""
        latency_ms = (time.perf_counter() - start_t) * 1000.0
        self.frame_latencies.append(latency_ms)

    def add_tracking_detections(self, frame_idx: int, timestamp: float, tracked_objects: List[Dict[str, Any]], class_names: Dict[int, str]):
        """Records per-frame object detections with persistent track IDs."""
        for obj in tracked_objects:
            c_id = obj["class_id"]
            c_name = class_names.get(c_id, f"class_{c_id}")
            bbox = obj.get("bbox", [0, 0, 0, 0])
            
            self.tracking_records.append({
                "frame": frame_idx,
                "timestamp": round(timestamp, 3),
                "track_id": obj["track_id"],
                "class_id": c_id,
                "class_name": c_name,
                "confidence": round(float(obj.get("confidence", 0.90)), 3),
                "bbox_x1": bbox[0],
                "bbox_y1": bbox[1],
                "bbox_x2": bbox[2],
                "bbox_y2": bbox[3]
            })

    def add_zone_events(self, violations: List[Dict[str, Any]], timestamp: float):
        """Records spatial zone events (entry, dwell, blockage)."""
        for v in violations:
            self.zone_event_records.append({
                "track_id": v["track_id"],
                "zone_id": v["zone_id"],
                "zone_name": v["zone_name"],
                "event": v.get("status", "ACTIVE_VIOLATION"),
                "timestamp": round(timestamp, 2),
                "dwell_time": round(v.get("dwell_time_seconds", 0.0), 2),
                "severity": v.get("severity", "HIGH")
            })

    def compute_summary_metrics(self, unique_person_count: int, unique_counts_by_class: Dict[str, int], total_frames: int, dropped_frames: int = 0) -> Dict[str, Any]:
        """Calculates benchmark metrics (FPS, Latency, Unique People, ID Switches)."""
        total_time = max(0.001, time.time() - self.start_wall_time)
        avg_fps = round(total_frames / total_time, 2)
        avg_latency = round(sum(self.frame_latencies) / max(1, len(self.frame_latencies)), 2)

        return {
            "site_id": self.site_id,
            "camera_id": self.camera_id,
            "total_frames_processed": total_frames,
            "dropped_frames": dropped_frames,
            "average_fps": avg_fps,
            "average_latency_ms": avg_latency,
            "unique_person_count": unique_person_count,
            "unique_counts_by_class": unique_counts_by_class,
            "estimated_id_switches": self.id_switch_count,
            "total_detections_logged": len(self.tracking_records),
            "total_zone_events_logged": len(self.zone_event_records)
        }

    # ── Downstream Output Exporters (Required for Member 3 Integration) ──────────

    def export_output_a_tracking_results(self, output_csv_path: str):
        """
        Output A: tracking_results.csv
        Schema: frame, timestamp, track_id, class, confidence, bbox
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_csv_path)), exist_ok=True)
        if not self.tracking_records:
            return
        fieldnames = ["frame", "timestamp", "track_id", "class_id", "class_name", "confidence", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2"]
        with open(output_csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.tracking_records)

    def export_output_b_zone_events(self, output_csv_path: str):
        """
        Output B: zone_events.csv
        Schema: track_id, zone_id, zone_name, event, timestamp, dwell_time, severity
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_csv_path)), exist_ok=True)
        fieldnames = ["track_id", "zone_id", "zone_name", "event", "timestamp", "dwell_time", "severity"]
        with open(output_csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            if self.zone_event_records:
                writer.writerows(self.zone_event_records)

    def export_output_c_zone_summary(self, output_json_path: str, unique_person_count: int, zone_engine, counting_lines: Dict[str, Any]):
        """
        Output C: zone_summary.json
        Schema: site_id, camera_id, unique_person_count, total_entries, total_exits, zones
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_json_path)), exist_ok=True)
        total_in = sum(cl.entries for cl in zone_engine.counting_lines.values()) if zone_engine.counting_lines else 0
        total_out = sum(cl.exits for cl in zone_engine.counting_lines.values()) if zone_engine.counting_lines else 0

        zones_summary = []
        for z_key, z_meta in zone_engine.zones.items():
            # Calculate active and total dwell
            active_count = sum(1 for (t_id, zk) in zone_engine.dwell_tracker.keys() if zk == z_key)
            zones_summary.append({
                "zone_id": z_meta["id"],
                "zone_name": z_meta["name"],
                "zone_type": z_meta["type"],
                "alert_severity": z_meta["severity"],
                "current_occupancy": active_count,
                "blockage_threshold_seconds": z_meta["threshold"]
            })

        summary_payload = {
            "site_id": self.site_id,
            "camera_id": self.camera_id,
            "unique_person_count": unique_person_count,
            "total_entries": total_in,
            "total_exits": total_out,
            "counting_lines": {
                k: {"entries": v.entries, "exits": v.exits}
                for k, v in zone_engine.counting_lines.items()
            },
            "zones": zones_summary
        }

        with open(output_json_path, "w") as f:
            json.dump(summary_payload, f, indent=2)
