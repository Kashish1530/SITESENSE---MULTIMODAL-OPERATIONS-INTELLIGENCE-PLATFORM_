"""
zone_engine.py
Spatial polygon containment, ground contact calculation, dwell-time monitoring,
and bidirectional entry/exit line crossing counters.
"""
import json
import numpy as np
from shapely.geometry import Point, Polygon
from typing import Dict, List, Tuple, Optional, Union

class CountingLine:
    """Virtual line to count entries and exits."""
    def __init__(self, line_id: str, name: str, coords: List[List[int]], count_classes: List[int]):
        self.line_id = line_id
        self.name = name
        self.p1 = np.array(coords[0], dtype=float)
        self.p2 = np.array(coords[1], dtype=float)
        self.count_classes = set(count_classes)
        self.entries = 0
        self.exits = 0
        self.prev_positions: Dict[int, np.ndarray] = {}

    def _side(self, pt: np.ndarray) -> float:
        # Cross product to determine which side of the line vector (p2 - p1) the point lies on
        v = self.p2 - self.p1
        p = pt - self.p1
        return v[0] * p[1] - v[1] * p[0]

    def update(self, track_id: int, class_id: int, ground_pt: np.ndarray) -> Optional[str]:
        if self.count_classes and class_id not in self.count_classes:
            return None

        event = None
        if track_id in self.prev_positions:
            prev_pt = self.prev_positions[track_id]
            side_prev = self._side(prev_pt)
            side_curr = self._side(ground_pt)

            # If sides have different signs, the line was crossed
            if side_prev * side_curr < 0:
                if side_curr > 0:
                    self.entries += 1
                    event = "ENTERED"
                else:
                    self.exits += 1
                    event = "EXITED"

        self.prev_positions[track_id] = ground_pt
        return event

class ZoneEngine:
    def __init__(self, *args, **kwargs):
        """
        Accepts config as positional argument, or via config_path / config_source keyword.
        Supports both filepath strings (e.g. 'config/zones_warehouse.json')
        and dynamic dictionary payloads directly from Admin API (Screen 12 - M6.9).
        """
        if args:
            source = args[0]
        elif "config_path" in kwargs:
            source = kwargs["config_path"]
        elif "config_source" in kwargs:
            source = kwargs["config_source"]
        elif "config" in kwargs:
            source = kwargs["config"]
        else:
            raise ValueError("ZoneEngine requires a config path or dictionary.")
            
        self.reload_config(source)
        # Dwell time tracking: {(track_id, zone_key): {"entry_ts": float, "class_id": int}}
        self.dwell_tracker: Dict[Tuple[int, str], Dict] = {}

    def reload_config(self, config_source: Union[str, Dict]):
        """Dynamically reloads zone polygons without restarting the service."""
        if isinstance(config_source, dict):
            self.config = config_source
        else:
            with open(config_source, "r") as f:
                self.config = json.load(f)
            
        self.zones: Dict[str, Dict] = {}
        for z_key, z_val in self.config.get("zones", {}).items():
            self.zones[z_key] = {
                "id": z_val["zone_id"],
                "name": z_val["zone_name"],
                "type": z_val.get("zone_type", "exclusion"),
                "severity": z_val.get("alert_severity", "HIGH"),
                "polygon": Polygon(z_val["coordinates"]),
                "raw_coords": np.array(z_val["coordinates"], dtype=np.int32),
                "prohibited": set(z_val.get("prohibited_classes", [])),
                "threshold": float(z_val.get("blockage_threshold_seconds", 3.0)),
                "description": z_val.get("description", "")
            }

        # Initialize counting lines if present
        self.counting_lines: Dict[str, CountingLine] = {}
        for l_key, l_val in self.config.get("counting_lines", {}).items():
            self.counting_lines[l_key] = CountingLine(
                line_id=l_val["line_id"],
                name=l_val["name"],
                coords=l_val["coordinates"],
                count_classes=l_val.get("count_classes", [0])
            )

        # Dynamic Machinery Circular Danger Zone Configuration
        ddz_cfg = self.config.get("dynamic_danger_zones", {})
        raw_m_classes = ddz_cfg.get("machinery_classes", [11, 12, 14])
        raw_t_classes = ddz_cfg.get("target_classes", [0])
        self.dynamic_danger_config = {
            "enabled": bool(ddz_cfg.get("enabled", True)),
            "machinery_classes": set(int(c) for c in raw_m_classes if isinstance(c, (int, str)) and str(c).isdigit()),
            "target_classes": set(int(c) for c in raw_t_classes if isinstance(c, (int, str)) and str(c).isdigit()),
            "danger_radius_px": float(ddz_cfg.get("danger_radius_px", 180.0)),
            "warning_radius_px": float(ddz_cfg.get("warning_radius_px", 260.0)),
            "alert_severity": str(ddz_cfg.get("alert_severity", "CRITICAL")).upper(),
            "description": str(ddz_cfg.get("description", "Dynamic circular danger zone around heavy equipment"))
        }
        if not self.dynamic_danger_config["machinery_classes"]:
            self.dynamic_danger_config["machinery_classes"] = {11, 12, 14}
        if not self.dynamic_danger_config["target_classes"]:
            self.dynamic_danger_config["target_classes"] = {0}

        self.last_dynamic_danger_circles: List[Dict] = []
        self.last_proximity_alerts: List[Dict] = []

    @staticmethod
    def get_ground_contact_point(bbox: List[int]) -> Point:
        """Calculates bottom-center point [x_mid, y2]"""
        x1, y1, x2, y2 = bbox
        return Point((x1 + x2) / 2.0, float(y2))

    def evaluate_dynamic_machinery_danger_zones(
        self,
        tracked_objects: List[Dict],
        timestamp: float
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Evaluates dynamic circular danger zones around moving heavy machinery (forklifts, vehicles, machinery).
        If a person (target class) falls within danger_radius_px of any heavy machinery,
        triggers an immediate DANGER alert with person_id, machine_id, and exact pixel distance.

        Returns:
            proximity_alerts: List of danger alerts with person ID, machine ID, and distance in px.
            dynamic_circles: List of circular zone geometries for rendering on video frames.
        """
        if not self.dynamic_danger_config.get("enabled", True):
            self.last_dynamic_danger_circles = []
            self.last_proximity_alerts = []
            return [], []

        m_classes = self.dynamic_danger_config.get("machinery_classes", {11, 12, 14})
        t_classes = self.dynamic_danger_config.get("target_classes", {0})
        danger_r = float(self.dynamic_danger_config.get("danger_radius_px", 180.0))
        warning_r = float(self.dynamic_danger_config.get("warning_radius_px", danger_r * 1.4))
        severity = self.dynamic_danger_config.get("alert_severity", "CRITICAL")

        CLASS_NAMES = {
            0: "person", 1: "safety_helmet", 2: "safety_vest", 3: "fire_extinguisher",
            4: "fire_hose", 5: "pallet", 6: "fire", 7: "spill", 8: "safety_signage",
            9: "exit_sign", 10: "empty_shelf", 11: "forklift", 12: "vehicle",
            13: "obstacle", 14: "machinery", 15: "safety_cone"
        }

        machinery_objs = []
        person_objs = []

        for obj in tracked_objects:
            cid = obj.get("class_id")
            cname = str(obj.get("class_name", CLASS_NAMES.get(cid, ""))).lower()
            if cid in m_classes or cname in ["forklift", "machinery", "vehicle"]:
                machinery_objs.append(obj)
            elif cid in t_classes or cname == "person":
                person_objs.append(obj)

        proximity_alerts = []
        dynamic_circles = []
        violated_machine_ids = set()

        for m_obj in machinery_objs:
            m_id = m_obj["track_id"]
            m_cid = m_obj.get("class_id", 14)
            m_cname = m_obj.get("class_name", CLASS_NAMES.get(m_cid, "machinery"))
            m_bbox = m_obj["bbox"]

            m_cx = (m_bbox[0] + m_bbox[2]) / 2.0
            m_cy = float(m_bbox[3])  # bottom center of machine on floor

            for p_obj in person_objs:
                p_id = p_obj["track_id"]
                p_bbox = p_obj["bbox"]
                p_conf = float(p_obj.get("confidence", 0.90))
                p_px = (p_bbox[0] + p_bbox[2]) / 2.0
                p_py = float(p_bbox[3])

                dx = p_px - m_cx
                dy = p_py - m_cy
                dist_px = float(np.sqrt(dx * dx + dy * dy))

                if dist_px <= danger_r:
                    violated_machine_ids.add(m_id)
                    alert_msg = (
                        f"CRITICAL DANGER: Person ID #{p_id} is very near {m_cname.capitalize()} "
                        f"ID #{m_id} (Distance: {dist_px:.1f}px <= Limit: {danger_r:.0f}px)!"
                    )
                    proximity_alerts.append({
                        "zone_id": f"DANGER_ZONE_{m_cname.upper()}_{m_id}",
                        "zone_name": f"Dynamic Danger Zone ({m_cname.capitalize()} #{m_id})",
                        "zone_type": "dynamic_danger_zone",
                        "severity": severity,
                        "track_id": p_id,
                        "person_id": p_id,
                        "machine_id": m_id,
                        "machine_class": m_cname,
                        "machine_class_id": m_cid,
                        "distance_px": round(dist_px, 1),
                        "danger_radius_px": round(danger_r, 1),
                        "class_id": 0,
                        "confidence": p_conf,
                        "bbox": p_bbox,
                        "machine_bbox": m_bbox,
                        "person_pt": (int(round(p_px)), int(round(p_py))),
                        "machine_pt": (int(round(m_cx)), int(round(m_cy))),
                        "entry_timestamp": round(timestamp, 2),
                        "current_timestamp": round(timestamp, 2),
                        "dwell_time_seconds": 0.0,
                        "status": "DANGER_PROXIMITY_ALERT",
                        "alert_message": alert_msg
                    })

            dynamic_circles.append({
                "machine_id": m_id,
                "class_id": m_cid,
                "class_name": m_cname,
                "center": (int(round(m_cx)), int(round(m_cy))),
                "radius": int(round(danger_r)),
                "warning_radius": int(round(warning_r)),
                "is_violated": (m_id in violated_machine_ids),
                "bbox": m_bbox
            })

        self.last_dynamic_danger_circles = dynamic_circles
        self.last_proximity_alerts = proximity_alerts
        return proximity_alerts, dynamic_circles

    def evaluate_tracks(
        self,
        tracked_objects: List[Dict],
        timestamp: float,
        evaluate_machinery_danger: bool = True
    ) -> Tuple[List[Dict], List[Dict]]:
        active_zone_tracks = set()
        spatial_violations = []
        crossing_events = []

        # Evaluate Dynamic Heavy Machinery Danger Zones (Circular Proximity)
        if evaluate_machinery_danger and self.dynamic_danger_config.get("enabled", True):
            proximity_alerts, _ = self.evaluate_dynamic_machinery_danger_zones(tracked_objects, timestamp)
            spatial_violations.extend(proximity_alerts)

        for obj in tracked_objects:
            t_id = obj["track_id"]
            c_id = obj["class_id"]
            conf = float(obj.get("confidence", 0.90))
            ground_pt = self.get_ground_contact_point(obj["bbox"])
            ground_pt_np = np.array([ground_pt.x, ground_pt.y])

            # Update line crossing counters
            for l_key, c_line in self.counting_lines.items():
                cross_dir = c_line.update(t_id, c_id, ground_pt_np)
                if cross_dir:
                    crossing_events.append({
                        "line_id": c_line.line_id,
                        "line_name": c_line.name,
                        "track_id": t_id,
                        "class_id": c_id,
                        "direction": cross_dir,
                        "entries": c_line.entries,
                        "exits": c_line.exits,
                        "timestamp": timestamp
                    })

            # Check Zone violations
            for z_key, z_meta in self.zones.items():
                if z_meta["polygon"].contains(ground_pt):
                    active_zone_tracks.add((t_id, z_key))
                    
                    if c_id in z_meta["prohibited"]:
                        pair_key = (t_id, z_key)
                        if pair_key not in self.dwell_tracker:
                            self.dwell_tracker[pair_key] = {
                                "entry_ts": timestamp,
                                "class_id": c_id,
                                "zone_id": z_meta["id"],
                                "zone_name": z_meta["name"],
                                "severity": z_meta["severity"]
                            }
                        
                        entry_ts = self.dwell_tracker[pair_key]["entry_ts"]
                        dwell_time = timestamp - entry_ts
                        
                        if dwell_time >= z_meta["threshold"]:
                            spatial_violations.append({
                                "zone_id": z_meta["id"],
                                "zone_name": z_meta["name"],
                                "zone_type": z_meta["type"],
                                "severity": z_meta["severity"],
                                "track_id": t_id,
                                "class_id": c_id,
                                "confidence": conf,
                                "bbox": obj["bbox"],
                                "entry_timestamp": round(entry_ts, 2),
                                "current_timestamp": round(timestamp, 2),
                                "dwell_time_seconds": round(dwell_time, 2),
                                "status": "ACTIVE_VIOLATION"
                            })

        # Evict exited objects
        all_tracked_pairs = set(self.dwell_tracker.keys())
        exited_pairs = all_tracked_pairs - active_zone_tracks
        for pair in exited_pairs:
            del self.dwell_tracker[pair]

        return spatial_violations, crossing_events
