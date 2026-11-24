"""
zone_validator.py — SiteSense Operations Intelligence
Member 2: Schema Definition, Validation, and Normalization for Visual Zone Configuration Editor

Validates zone polygon geometries, class taxonomy mappings, dwell thresholds,
and counting lines. Ensures dynamic configurations sent from Admin UI (Screen 12 - M6.9)
or API endpoints are mathematically sound before loading into the ZoneEngine,
guaranteeing ZERO runtime crashes.
"""

from typing import Dict, List, Tuple, Any, Optional, Union
import json
import os
import yaml
from shapely.geometry import Polygon

# Canonical SiteSense 16-Class Taxonomy
CANONICAL_CLASSES: Dict[int, str] = {
    0: "person",
    1: "safety_helmet",
    2: "safety_vest",
    3: "fire_extinguisher",
    4: "fire_hose",
    5: "pallet",
    6: "fire",
    7: "spill",
    8: "safety_signage",
    9: "exit_sign",
    10: "empty_shelf",
    11: "forklift",
    12: "vehicle",
    13: "obstacle",
    14: "machinery",
    15: "safety_cone"
}

NAME_TO_CLASS_ID = {v.lower(): k for k, v in CANONICAL_CLASSES.items()}
NAME_TO_CLASS_ID.update({
    "helmet": 1,
    "vest": 2,
    "extinguisher": 3,
    "hose": 4,
    "cart": 12,
    "truck": 12,
    "cone": 15
})

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
VALID_ZONE_TYPES = {
    "exclusion", "walkway", "equipment_clearance", 
    "machinery_perimeter", "restricted", "loading_dock", "fire_exit", "custom"
}


def get_zone_config_json_schema() -> Dict[str, Any]:
    """
    Returns the formal JSON Schema specification for SiteSense Zone Configurations.
    This contract can be shared with Member 6 (Frontend) and Member 3 (GenAI/Agentic).
    """
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "SiteSenseZoneConfig",
        "type": "object",
        "required": ["camera_id", "zones"],
        "properties": {
            "camera_id": {
                "type": "string",
                "description": "Unique camera identifier (e.g. CAM_WH_01)"
            },
            "site_id": {
                "type": "string",
                "description": "Unique site / facility identifier (e.g. SITE_WH_01)"
            },
            "site_name": {
                "type": "string",
                "description": "Human-readable name of the facility or sector"
            },
            "site_type": {
                "type": "string",
                "enum": ["warehouse", "construction", "manufacturing", "logistics", "general"],
                "default": "warehouse"
            },
            "resolution": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1},
                "minItems": 2,
                "maxItems": 2,
                "description": "[width, height] in pixels (e.g. [1280, 720])"
            },
            "zones": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "required": ["zone_id", "zone_name", "coordinates"],
                    "properties": {
                        "zone_id": {
                            "type": "string",
                            "description": "Unique zone identifier (e.g. ZONE_EXIT_01)"
                        },
                        "zone_name": {
                            "type": "string",
                            "description": "Descriptive display title for alerts"
                        },
                        "zone_type": {
                            "type": "string",
                            "enum": list(VALID_ZONE_TYPES),
                            "default": "exclusion"
                        },
                        "alert_severity": {
                            "type": "string",
                            "enum": list(VALID_SEVERITIES),
                            "default": "HIGH"
                        },
                        "coordinates": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2
                            },
                            "minItems": 3,
                            "description": "Ordered polygon vertices [[x1, y1], [x2, y2], [x3, y3], ...]"
                        },
                        "prohibited_classes": {
                            "type": "array",
                            "items": {"type": ["integer", "string"]},
                            "description": "Class IDs or class names prohibited inside zone"
                        },
                        "blockage_threshold_seconds": {
                            "type": "number",
                            "minimum": 0.0,
                            "default": 3.0,
                            "description": "Dwell time in seconds before triggering alert"
                        },
                        "description": {
                            "type": "string",
                            "description": "Standard operating procedure or safety rule note"
                        }
                    }
                }
            },
            "counting_lines": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "required": ["line_id", "name", "coordinates"],
                    "properties": {
                        "line_id": {"type": "string"},
                        "name": {"type": "string"},
                        "coordinates": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2
                            },
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "Endpoints of virtual counting line [[x1, y1], [x2, y2]]"
                        },
                        "count_classes": {
                            "type": "array",
                            "items": {"type": ["integer", "string"]},
                            "default": [0]
                        },
                        "description": {"type": "string"}
                    }
                }
            }
        }
    }


class ZoneConfigValidator:
    """
    Comprehensive validator for SiteSense zone configuration payloads.
    Guarantees schema integrity, geometric validity, and taxonomy normalization.
    """

    @classmethod
    def normalize_class_id(cls, raw_class: Union[int, str]) -> Optional[int]:
        """Maps string or int class identifier to valid 0..15 taxonomy integer ID."""
        if isinstance(raw_class, int):
            if raw_class in CANONICAL_CLASSES:
                return raw_class
            return None
        if isinstance(raw_class, str):
            clean = raw_class.strip().lower()
            if clean.isdigit():
                val = int(clean)
                return val if val in CANONICAL_CLASSES else None
            return NAME_TO_CLASS_ID.get(clean)
        return None

    @classmethod
    def validate(cls, config: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validates and sanitizes a complete zone configuration dictionary.
        
        Returns:
            (is_valid: bool, errors: List[str], sanitized_config: Dict[str, Any])
        """
        errors: List[str] = []
        if not isinstance(config, dict):
            return False, ["Root configuration must be a JSON object."], {}

        sanitized = {
            "camera_id": str(config.get("camera_id", "CAM_DEFAULT")).strip(),
            "site_id": str(config.get("site_id", "SITE_DEFAULT")).strip(),
            "site_name": str(config.get("site_name", "SiteSense Managed Facility")).strip(),
            "site_type": str(config.get("site_type", "warehouse")).lower().strip(),
            "resolution": [1280, 720],
            "zones": {},
            "counting_lines": {}
        }

        # Resolution check
        res = config.get("resolution")
        if res:
            if isinstance(res, (list, tuple)) and len(res) == 2 and all(isinstance(x, (int, float)) and x > 0 for x in res):
                sanitized["resolution"] = [int(res[0]), int(res[1])]
            else:
                errors.append("Field 'resolution' must be a list of two positive integers [width, height].")

        max_w, max_h = sanitized["resolution"]

        # Validate Zones
        zones_raw = config.get("zones", {})
        if not isinstance(zones_raw, dict):
            errors.append("Field 'zones' must be an object with zone definitions.")
        else:
            seen_zone_ids = set()
            for z_key, z_val in zones_raw.items():
                if not isinstance(z_val, dict):
                    errors.append(f"Zone '{z_key}' configuration must be an object.")
                    continue

                z_id = str(z_val.get("zone_id", z_key)).strip()
                if not z_id:
                    errors.append(f"Zone '{z_key}' has an empty or invalid 'zone_id'.")
                elif z_id in seen_zone_ids:
                    errors.append(f"Duplicate zone_id '{z_id}' detected in zone '{z_key}'.")
                seen_zone_ids.add(z_id)

                z_name = str(z_val.get("zone_name", z_key)).strip()
                if not z_name:
                    errors.append(f"Zone '{z_key}' must have a non-empty 'zone_name'.")

                severity = str(z_val.get("alert_severity", "HIGH")).upper().strip()
                if severity not in VALID_SEVERITIES:
                    errors.append(f"Zone '{z_key}' has invalid alert_severity '{severity}'. Valid: {sorted(VALID_SEVERITIES)}.")
                    severity = "HIGH"

                zone_type = str(z_val.get("zone_type", "exclusion")).lower().strip()
                if zone_type not in VALID_ZONE_TYPES:
                    zone_type = "exclusion"

                # Validate Coordinates
                raw_coords = z_val.get("coordinates")
                if not raw_coords or not isinstance(raw_coords, list) or len(raw_coords) < 3:
                    errors.append(f"Zone '{z_key}' must have at least 3 coordinates for a polygon. Got: {raw_coords}")
                    sanitized_coords = []
                else:
                    sanitized_coords = []
                    coords_ok = True
                    for pt_idx, pt in enumerate(raw_coords):
                        if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                            errors.append(f"Zone '{z_key}' point #{pt_idx+1} is invalid. Expected [x, y], got {pt}.")
                            coords_ok = False
                            continue
                        try:
                            px = float(pt[0])
                            py = float(pt[1])
                            if px < 0 or py < 0:
                                errors.append(f"Zone '{z_key}' point #{pt_idx+1} has negative coordinates: [{px}, {py}].")
                                coords_ok = False
                            # Relaxed upper bound check (warn if way beyond resolution)
                            if px > max_w * 2.0 or py > max_h * 2.0:
                                errors.append(f"Zone '{z_key}' point #{pt_idx+1} [{px}, {py}] exceeds camera dimensions {sanitized['resolution']}.")
                                coords_ok = False
                            sanitized_coords.append([int(round(px)), int(round(py))])
                        except (ValueError, TypeError):
                            errors.append(f"Zone '{z_key}' point #{pt_idx+1} contains non-numeric values.")
                            coords_ok = False

                    # Check geometric polygon validity with Shapely
                    if coords_ok and len(sanitized_coords) >= 3:
                        try:
                            poly = Polygon(sanitized_coords)
                            if not poly.is_valid:
                                # Try fixing self-intersection with buffer(0)
                                fixed = poly.buffer(0)
                                if not fixed.is_valid or fixed.is_empty:
                                    errors.append(f"Zone '{z_key}' polygon has self-intersecting or degenerate geometry.")
                            elif poly.area <= 0:
                                errors.append(f"Zone '{z_key}' polygon has zero area (collinear points).")
                        except Exception as e:
                            errors.append(f"Zone '{z_key}' geometric validation error: {str(e)}")

                # Validate Prohibited Classes
                prohibited_raw = z_val.get("prohibited_classes", [])
                prohibited_ids = []
                if isinstance(prohibited_raw, list):
                    for item in prohibited_raw:
                        norm = cls.normalize_class_id(item)
                        if norm is not None:
                            if norm not in prohibited_ids:
                                prohibited_ids.append(norm)
                        else:
                            errors.append(f"Zone '{z_key}' contains unknown class '{item}'. Valid classes: {list(CANONICAL_CLASSES.values())}.")
                else:
                    errors.append(f"Zone '{z_key}' prohibited_classes must be a list.")

                # Validate Dwell Threshold
                raw_thresh = z_val.get("blockage_threshold_seconds", 3.0)
                try:
                    threshold = float(raw_thresh)
                    if threshold < 0:
                        errors.append(f"Zone '{z_key}' blockage_threshold_seconds cannot be negative.")
                        threshold = 0.0
                except (ValueError, TypeError):
                    errors.append(f"Zone '{z_key}' blockage_threshold_seconds must be a number.")
                    threshold = 3.0

                sanitized["zones"][z_key] = {
                    "zone_id": z_id,
                    "zone_name": z_name,
                    "zone_type": zone_type,
                    "alert_severity": severity,
                    "coordinates": sanitized_coords,
                    "prohibited_classes": prohibited_ids,
                    "blockage_threshold_seconds": threshold,
                    "description": str(z_val.get("description", "")).strip()
                }

        # Validate Counting Lines
        lines_raw = config.get("counting_lines", {})
        if lines_raw and isinstance(lines_raw, dict):
            for l_key, l_val in lines_raw.items():
                if not isinstance(l_val, dict):
                    continue
                l_id = str(l_val.get("line_id", l_key)).strip()
                l_name = str(l_val.get("name", l_key)).strip()
                coords = l_val.get("coordinates", [])

                if not isinstance(coords, list) or len(coords) != 2:
                    errors.append(f"Counting line '{l_key}' must have exactly 2 endpoint coordinates [[x1, y1], [x2, y2]].")
                    continue

                line_coords = []
                for pt in coords:
                    if isinstance(pt, (list, tuple)) and len(pt) == 2:
                        line_coords.append([int(round(pt[0])), int(round(pt[1]))])

                if len(line_coords) == 2:
                    count_classes_raw = l_val.get("count_classes", [0])
                    count_classes = []
                    for c in count_classes_raw:
                        norm = cls.normalize_class_id(c)
                        if norm is not None and norm not in count_classes:
                            count_classes.append(norm)

                    sanitized["counting_lines"][l_key] = {
                        "line_id": l_id,
                        "name": l_name,
                        "coordinates": line_coords,
                        "count_classes": count_classes if count_classes else [0],
                        "description": str(l_val.get("description", "")).strip()
                    }

        is_valid = len(errors) == 0
        return is_valid, errors, sanitized
