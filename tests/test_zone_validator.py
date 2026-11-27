"""
test_zone_validator.py — SiteSense Operations Intelligence
Validates JSON schema, geometric sanity checks, taxonomy mapping,
and dynamic zone configuration rules for Member 2.
"""

import pytest
import os
import sys

sys.path.append(os.path.abspath("src"))
from zone_validator import ZoneConfigValidator, get_zone_config_json_schema, CANONICAL_CLASSES


def test_schema_structure():
    schema = get_zone_config_json_schema()
    assert isinstance(schema, dict)
    assert schema["title"] == "SiteSenseZoneConfig"
    assert "camera_id" in schema["required"]
    assert "zones" in schema["required"]


def test_valid_zone_config_validation():
    valid_payload = {
        "camera_id": "CAM_WH_01",
        "site_id": "SITE_WH_01",
        "site_name": "Main Logistics Hub",
        "resolution": [1280, 720],
        "zones": {
            "emergency_exit": {
                "zone_id": "ZONE_EXIT_01",
                "zone_name": "Emergency Fire Exit Doorway",
                "zone_type": "exclusion",
                "alert_severity": "CRITICAL",
                "coordinates": [[480, 340], [920, 340], [920, 700], [480, 700]],
                "prohibited_classes": ["pallet", "forklift", 0],  # Mixed string and int
                "blockage_threshold_seconds": 3.0,
                "description": "Evacuation corridor must stay clear."
            }
        },
        "counting_lines": {
            "main_door_counter": {
                "line_id": "LINE_01",
                "name": "Pedestrian Ingress Counter",
                "coordinates": [[700, 360], [950, 600]],
                "count_classes": ["person"]
            }
        }
    }

    is_valid, errors, sanitized = ZoneConfigValidator.validate(valid_payload)
    assert is_valid is True, f"Expected valid payload but got errors: {errors}"
    assert len(errors) == 0
    assert "emergency_exit" in sanitized["zones"]
    # Verify class names were normalized to ints
    prohibited = sanitized["zones"]["emergency_exit"]["prohibited_classes"]
    assert 5 in prohibited  # pallet
    assert 11 in prohibited  # forklift
    assert 0 in prohibited  # person


def test_invalid_polygon_fewer_than_3_points():
    invalid_payload = {
        "camera_id": "CAM_01",
        "zones": {
            "bad_zone": {
                "zone_id": "Z_BAD",
                "zone_name": "Too few vertices",
                "coordinates": [[100, 100], [200, 200]],  # Only 2 points
                "alert_severity": "HIGH"
            }
        }
    }
    is_valid, errors, sanitized = ZoneConfigValidator.validate(invalid_payload)
    assert is_valid is False
    assert any("at least 3 coordinates" in e for e in errors)


def test_invalid_negative_coordinates():
    invalid_payload = {
        "camera_id": "CAM_01",
        "zones": {
            "bad_coords": {
                "zone_id": "Z_NEG",
                "zone_name": "Negative Coords Zone",
                "coordinates": [[-50, 100], [150, 100], [150, 300]],
                "alert_severity": "MEDIUM"
            }
        }
    }
    is_valid, errors, sanitized = ZoneConfigValidator.validate(invalid_payload)
    assert is_valid is False
    assert any("negative" in e.lower() for e in errors)


def test_invalid_severity_and_negative_dwell():
    invalid_payload = {
        "camera_id": "CAM_01",
        "zones": {
            "bad_rules": {
                "zone_id": "Z_RULES",
                "zone_name": "Bad Severity Zone",
                "coordinates": [[100, 100], [300, 100], [300, 300], [100, 300]],
                "alert_severity": "ULTRA_LETHAL",  # Invalid
                "blockage_threshold_seconds": -5.0  # Invalid negative
            }
        }
    }
    is_valid, errors, sanitized = ZoneConfigValidator.validate(invalid_payload)
    assert is_valid is False
    assert any("alert_severity" in e for e in errors)
    assert any("negative" in e for e in errors)


def test_counting_line_requires_two_points():
    invalid_payload = {
        "camera_id": "CAM_01",
        "zones": {
            "valid_zone": {
                "zone_id": "Z_OK",
                "zone_name": "Valid Zone",
                "coordinates": [[100, 100], [300, 100], [300, 300]],
                "alert_severity": "LOW"
            }
        },
        "counting_lines": {
            "bad_line": {
                "line_id": "L1",
                "name": "Too many points for a line",
                "coordinates": [[10, 10], [50, 50], [100, 100]]
            }
        }
    }
    is_valid, errors, sanitized = ZoneConfigValidator.validate(invalid_payload)
    assert is_valid is False
    assert any("exactly 2 endpoint coordinates" in e for e in errors)
