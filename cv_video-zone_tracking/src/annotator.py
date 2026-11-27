"""
annotator.py
Professional Computer Vision Annotator compliant with:
- Feature 2.6: Annotated Output Generation (Boxes, Labels, Zones, Track IDs, Confidence, Alerts)
- classes.yaml (Taxonomy RGB/BGR Colors & 16 Classes)
- Virtual Counting Line overlay & HUD Counters
"""
import cv2
import numpy as np
from typing import List, Dict, Any

CLASS_COLORS_BGR = {
    0: (255, 128, 0),    # person: [0, 128, 255] RGB -> BGR
    1: (0, 215, 255),    # safety_helmet: [255, 215, 0]
    2: (50, 205, 50),    # safety_vest: [50, 205, 50]
    3: (60, 20, 220),    # fire_extinguisher: [220, 20, 60]
    4: (34, 34, 178),    # fire_hose: [178, 34, 34]
    5: (45, 82, 160),    # pallet: [160, 82, 45]
    6: (0, 69, 255),     # fire: [255, 69, 0]
    7: (255, 191, 0),    # spill: [0, 191, 255]
    8: (0, 165, 255),    # safety_signage: [255, 165, 0]
    9: (83, 200, 0),     # exit_sign: [0, 200, 83]
    10: (219, 112, 147), # empty_shelf: [147, 112, 219]
    11: (0, 140, 255),   # forklift: [255, 140, 0]
    12: (180, 130, 70),  # vehicle: [70, 130, 180]
    13: (127, 0, 255),   # obstacle: [255, 0, 127]
    14: (32, 165, 218),  # machinery: [218, 165, 32]
    15: (71, 99, 255)    # safety_cone: [255, 99, 71]
}

CLASS_NAMES = {
    0: "person", 1: "safety_helmet", 2: "safety_vest", 3: "fire_extinguisher",
    4: "fire_hose", 5: "pallet", 6: "fire", 7: "spill", 8: "safety_signage",
    9: "exit_sign", 10: "empty_shelf", 11: "forklift", 12: "vehicle",
    13: "obstacle", 14: "machinery", 15: "safety_cone"
}

class VisualAnnotator:
    CLASS_NAMES = CLASS_NAMES
    CLASS_COLORS_BGR = CLASS_COLORS_BGR
    @staticmethod
    def draw_zones(frame: np.ndarray, zones: Dict[str, Any], active_violation_zones: set = None) -> np.ndarray:
        if not zones:
            return frame
        if active_violation_zones is None:
            active_violation_zones = set()

        try:
            overlay = frame.copy()
            for z_key, z_meta in zones.items():
                pts = [z_meta["raw_coords"]]
                is_violated = z_meta["id"] in active_violation_zones
                
                if is_violated:
                    color = (0, 0, 230)
                    border_color = (0, 0, 255)
                elif z_meta["severity"] == "CRITICAL":
                    color = (0, 120, 220)
                    border_color = (0, 165, 255)
                else:
                    color = (180, 120, 0)
                    border_color = (220, 180, 0)

                cv2.fillPoly(overlay, pts, color)
                cv2.polylines(frame, pts, True, border_color, 2, cv2.LINE_AA)
                
                label_pos = (z_meta["raw_coords"][0][0], z_meta["raw_coords"][0][1] - 8)
                cv2.putText(frame, z_meta["name"].upper(), label_pos,
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, border_color, 2, cv2.LINE_AA)

            cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)
            del overlay
        except (MemoryError, Exception):
            # In-place zero-allocation fallback if memory is constrained
            for z_key, z_meta in zones.items():
                pts = [z_meta["raw_coords"]]
                is_violated = z_meta["id"] in active_violation_zones
                border_color = (0, 0, 255) if is_violated else (0, 165, 255)
                cv2.polylines(frame, pts, True, border_color, 2, cv2.LINE_AA)
                label_pos = (z_meta["raw_coords"][0][0], z_meta["raw_coords"][0][1] - 8)
                cv2.putText(frame, z_meta["name"].upper(), label_pos,
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, border_color, 2, cv2.LINE_AA)

        return frame

    @staticmethod
    def draw_counting_lines(frame: np.ndarray, counting_lines: Dict[str, Any]) -> np.ndarray:
        """Draws virtual crossing lines with entry/exit count badges."""
        for l_key, c_line in counting_lines.items():
            pt1 = (int(c_line.p1[0]), int(c_line.p1[1]))
            pt2 = (int(c_line.p2[0]), int(c_line.p2[1]))
            
            # Line
            cv2.line(frame, pt1, pt2, (255, 255, 0), 3, cv2.LINE_AA)
            cv2.circle(frame, pt1, 5, (0, 255, 255), -1)
            cv2.circle(frame, pt2, 5, (0, 255, 255), -1)

            # Badge
            mid_x = (pt1[0] + pt2[0]) // 2
            mid_y = (pt1[1] + pt2[1]) // 2
            badge = f"{c_line.name}: IN {c_line.entries} | OUT {c_line.exits}"
            cv2.putText(frame, badge, (mid_x - 60, mid_y - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 0), 2, cv2.LINE_AA)
        return frame

    @staticmethod
    def draw_tracked_objects(frame: np.ndarray, tracked_objects: List[Dict[str, Any]], violations: List[Dict]) -> np.ndarray:
        violating_track_ids = {v["track_id"] for v in violations}

        for obj in tracked_objects:
            t_id = obj["track_id"]
            c_id = obj["class_id"]
            conf = obj.get("confidence", 0.0)
            x1, y1, x2, y2 = obj["bbox"]
            
            is_viol = t_id in violating_track_ids
            box_color = (0, 0, 255) if is_viol else CLASS_COLORS_BGR.get(c_id, (0, 255, 0))
            
            thickness = 3 if is_viol else 2
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, thickness, cv2.LINE_AA)
            
            # Ground Contact Point
            ground_x = (x1 + x2) // 2
            ground_y = y2
            cv2.circle(frame, (ground_x, ground_y), 4, (0, 0, 255) if is_viol else (0, 255, 255), -1)

            # Label Header Badge
            c_name = CLASS_NAMES.get(c_id, f"cls_{c_id}")
            badge_text = f"ID:{t_id} {c_name} {conf:.2f}"
            if is_viol:
                badge_text += " [VIOLATION]"

            (tw, th), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (x1, max(0, y1 - th - 6)), (x1 + tw + 6, y1), box_color, -1)
            cv2.putText(frame, badge_text, (x1 + 3, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        return frame

    @staticmethod
    def draw_dynamic_danger_zones(
        frame: np.ndarray,
        dynamic_danger_circles: List[Dict[str, Any]],
        proximity_alerts: List[Dict[str, Any]]
    ) -> np.ndarray:
        """
        Renders dynamic circular danger zones around moving heavy machinery (forklifts, vehicles, machinery)
        and draws distance vectors with danger badges between persons and machines in danger proximity.
        """
        if not dynamic_danger_circles and not proximity_alerts:
            return frame

        h, w = frame.shape[:2]

        # 1. Draw circular danger zones around heavy machinery
        for circle in dynamic_danger_circles:
            cx, cy = circle["center"]
            radius = int(circle["radius"])
            warning_r = int(circle.get("warning_radius", radius * 1.35))
            is_violated = circle["is_violated"]
            m_name = str(circle.get("class_name", "machinery")).title()
            m_id = circle.get("machine_id", "")

            if is_violated:
                danger_bgr = (0, 0, 255)  # Bright Red
                # Draw shaded circular danger halo in ROI (zero-copy / low-memory)
                x_min = max(0, cx - radius)
                x_max = min(w, cx + radius)
                y_min = max(0, cy - radius)
                y_max = min(h, cy + radius)
                if x_max > x_min and y_max > y_min:
                    try:
                        roi = frame[y_min:y_max, x_min:x_max]
                        mask = np.zeros((y_max - y_min, x_max - x_min), dtype=np.uint8)
                        cv2.circle(mask, (cx - x_min, cy - y_min), radius, 255, -1)
                        red_patch = np.full_like(roi, (0, 0, 230))
                        cv2.copyTo(cv2.addWeighted(red_patch, 0.28, roi, 0.72, 0), mask, roi)
                    except Exception:
                        pass

                # Outer warning perimeter circle
                cv2.circle(frame, (cx, cy), warning_r, (0, 140, 255), 1, cv2.LINE_AA)
                # Primary Danger circle boundary
                cv2.circle(frame, (cx, cy), radius, danger_bgr, 3, cv2.LINE_AA)

                # Danger Zone Header Badge
                badge = f"!! DANGER ZONE: {m_name} #{m_id} [R={radius}px]"
                (tw, th), _ = cv2.getTextSize(badge, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
                bx = max(10, cx - tw // 2)
                by = max(th + 10, cy - radius - 10)
                cv2.rectangle(frame, (bx - 4, by - th - 4), (bx + tw + 4, by + 4), (0, 0, 180), -1)
                cv2.rectangle(frame, (bx - 4, by - th - 4), (bx + tw + 4, by + 4), (0, 0, 255), 2)
                cv2.putText(frame, badge, (bx, by), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

            else:
                # Safe state: Cyan / Safety Yellow circular perimeter
                safe_bgr = (0, 215, 255)
                cv2.circle(frame, (cx, cy), radius, safe_bgr, 2, cv2.LINE_AA)
                badge = f"{m_name} #{m_id} Danger Perimeter (R={radius}px)"
                cv2.putText(frame, badge, (max(10, cx - 100), max(20, cy - radius - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, safe_bgr, 1, cv2.LINE_AA)

        # 2. Draw connector lines and pixel distance badges for proximity alerts
        for alert in proximity_alerts:
            p_pt = alert["person_pt"]
            m_pt = alert["machine_pt"]
            dist = alert["distance_px"]
            p_id = alert["person_id"]
            m_id = alert["machine_id"]
            m_name = alert["machine_class"].title()

            # High-visibility connecting danger line
            cv2.line(frame, p_pt, m_pt, (0, 0, 255), 2, cv2.LINE_AA)
            cv2.circle(frame, p_pt, 6, (0, 0, 255), -1)
            cv2.circle(frame, m_pt, 6, (0, 0, 255), -1)

            # Midpoint distance badge
            mid_x = (p_pt[0] + m_pt[0]) // 2
            mid_y = (p_pt[1] + m_pt[1]) // 2
            dist_text = f"DANGER: {dist:.1f}px (Person #{p_id} <-> {m_name} #{m_id})"
            (tw, th), _ = cv2.getTextSize(dist_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (mid_x - tw // 2 - 5, mid_y - th - 5),
                          (mid_x + tw // 2 + 5, mid_y + 5), (0, 0, 160), -1)
            cv2.rectangle(frame, (mid_x - tw // 2 - 5, mid_y - th - 5),
                          (mid_x + tw // 2 + 5, mid_y + 5), (0, 0, 255), 1)
            cv2.putText(frame, dist_text, (mid_x - tw // 2, mid_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        return frame

    @staticmethod
    def draw_hud(frame: np.ndarray, frame_idx: int, timestamp: float, active_violations: List[Dict], total_tracks: int, counting_lines: Dict[str, Any] = None) -> np.ndarray:
        h, w = frame.shape[:2]
        
        # Zero-copy in-place darkening for HUD header banner (prevents ArrayMemoryError)
        try:
            hud_h = min(56, h)
            roi = frame[0:hud_h, 0:w]
            cv2.convertScaleAbs(roi, roi, alpha=0.30, beta=12)
            cv2.line(frame, (0, hud_h), (w, hud_h), (50, 50, 50), 1)
        except Exception:
            pass

        # Status Line
        counts_summary = ""
        if counting_lines:
            for cl in counting_lines.values():
                counts_summary += f" | {cl.name}: IN={cl.entries} OUT={cl.exits}"

        status_text = f"SiteSense CV Engine | Frame: {frame_idx:04d} | Time: {timestamp:.1f}s | Tracks: {total_tracks}{counts_summary}"
        cv2.putText(frame, status_text, (15, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (240, 240, 240), 1, cv2.LINE_AA)

        if active_violations:
            alert_count = len(active_violations)
            cv2.putText(frame, f"ALERTS: {alert_count} ACTIVE", (15, 46),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2, cv2.LINE_AA)
            for idx, viol in enumerate(active_violations[:2]):
                if viol.get("zone_type") == "dynamic_danger_zone":
                    msg = f"! [DANGER] Person #{viol.get('person_id', viol['track_id'])} NEAR {str(viol.get('machine_class', 'Machinery')).title()} #{viol.get('machine_id', '')} ({viol.get('distance_px', 0)}px)"
                else:
                    c_name = CLASS_NAMES.get(viol['class_id'], 'object')
                    msg = f"! [{viol['severity']}] {viol['zone_name']}: {c_name} ({viol['dwell_time_seconds']}s)"
                cv2.putText(frame, msg, (220, 46 + idx * 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 255), 1, cv2.LINE_AA)
        else:
            cv2.putText(frame, "STATUS: ALL ZONES SECURE (NO OBSTRUCTIONS)", (15, 46),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (50, 205, 50), 2, cv2.LINE_AA)

        return frame
