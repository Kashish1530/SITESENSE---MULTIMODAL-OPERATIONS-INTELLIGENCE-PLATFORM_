import uuid
from typing import Dict, Any

class SpatialEventFormatter:
    CLASS_LOOKUP = {
        0: "person", 1: "safety_helmet", 2: "safety_vest", 3: "fire_extinguisher",
        4: "fire_hose", 5: "pallet", 6: "fire", 7: "spill", 8: "safety_signage",
        9: "exit_sign", 10: "empty_shelf", 11: "forklift", 12: "vehicle",
        13: "obstacle", 14: "machinery", 15: "safety_cone"
    }

    @classmethod
    def format_event(cls, violation: Dict[str, Any], site_id: str, camera_id: str) -> Dict[str, Any]:
        """
        Creates a standardized JSON payload consumed by:
        1. Member 3 Compliance Engine (Checks rule & draws evidence)
        2. Member 4 Agentic Layer (Tool: get_site_findings)
        3. Reviewer Queue (Flags low-confidence detections for human review)
        4. Central Violation Database (Table: violations)
        """
        c_id = violation["class_id"]
        class_name = cls.CLASS_LOOKUP.get(c_id, f"class_{c_id}")
        zone_type = violation.get("zone_type", "exclusion")
        zone_name_lower = violation.get("zone_name", "").lower()
        
        # Categorize spatial incident type
        if zone_type in ["dynamic_danger_zone", "dynamic_proximity"] or "danger" in zone_name_lower or "machinery" in zone_name_lower or "crane" in zone_name_lower or zone_type == "proximity_exclusion":
            event_type = "MACHINERY_PROXIMITY_HAZARD"
        elif "exit" in zone_name_lower or zone_type == "exclusion":
            event_type = "EMERGENCY_EXIT_BLOCKED"
        elif "extinguisher" in zone_name_lower or "equipment" in zone_name_lower or zone_type == "equipment_clearance" or ("fire" in zone_name_lower and "exit" not in zone_name_lower):
            event_type = "FIRE_EQUIPMENT_OBSTRUCTED"
        elif "aisle" in zone_name_lower or "walkway" in zone_name_lower or zone_type == "walkway":
            event_type = "WALKWAY_OBSTRUCTED"
        else:
            event_type = "ZONE_INTRUSION"

        conf = float(violation.get("confidence", 0.90))
        # Human-in-the-loop review threshold (< 70% confidence sent to Reviewer Queue)
        needs_human_review = bool(conf < 0.70)

        target_payload = {
            "track_id": violation["track_id"],
            "class_id": c_id,
            "class_name": class_name,
            "confidence": round(conf, 3),
            "bbox_xyxy": violation["bbox"]
        }
        if zone_type == "dynamic_danger_zone":
            target_payload.update({
                "person_id": violation.get("person_id", violation["track_id"]),
                "machine_id": violation.get("machine_id"),
                "machine_class": violation.get("machine_class"),
                "distance_px": violation.get("distance_px"),
                "danger_radius_px": violation.get("danger_radius_px")
            })
            rec_action = (
                f"CRITICAL: Worker #{violation.get('person_id', violation['track_id'])} must step back immediately "
                f"from {str(violation.get('machine_class', 'machinery')).title()} #{violation.get('machine_id', '')} "
                f"(Distance: {violation.get('distance_px', 0)}px <= Limit: {violation.get('danger_radius_px', 180)}px)!"
            )
        else:
            rec_action = f"Remove {class_name} from {violation['zone_name']} immediately."

        return {
            "event_id": f"EVT_{uuid.uuid4().hex[:8].upper()}",
            "site_id": site_id,
            "camera_id": camera_id,
            "event_type": event_type,
            "severity": violation["severity"],
            "zone_id": violation["zone_id"],
            "zone_name": violation["zone_name"],
            "target": target_payload,
            "temporal": {
                "entry_timestamp": violation["entry_timestamp"],
                "current_timestamp": violation["current_timestamp"],
                "dwell_time_seconds": violation["dwell_time_seconds"]
            },
            "status": violation["status"],
            "confidence": round(conf, 3),
            "needs_human_review": needs_human_review,
            "associated_ppe": violation.get("associated_ppe", []),
            "evidence_required": True,
            "recommended_action": rec_action
        }
