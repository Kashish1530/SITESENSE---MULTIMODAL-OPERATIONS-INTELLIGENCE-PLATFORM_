"""
SITESENSE - Policy Rules Synchronizer
Populates machine-readable compliance rules in Neon DB for all 16 CV classes,
linking each rule directly to its official Policy Handbook Clause.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

load_dotenv(Path(__file__).resolve().parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")

RULES = [
    {
        "name": "Walkway Obstruction Rule",
        "description": "Primary transit corridors must maintain at least 1.2m clear width. Pallets and obstacles are forbidden.",
        "rule_type": "zone_clear",
        "parameters": {
            "zone": "main_walkway",
            "forbidden_classes": ["pallets", "obstacle"],
            "min_clearance_meters": 1.2
        },
        "policy_ref": "Clause 4.1 - Primary Walkway Minimum Clearance"
    },
    {
        "name": "Fire Exit Clearance Rule",
        "description": "Zero tolerance for any obstruction within 2.0m of emergency exit doors.",
        "rule_type": "forbidden_object_absent",
        "parameters": {
            "zone": "emergency_exit",
            "forbidden_classes": ["pallets", "obstacle"],
            "trigger_class": "exit-sign"
        },
        "policy_ref": "Clause 4.2 - Emergency Fire Exit Zero-Tolerance Clearance"
    },
    {
        "name": "PPE Safety Helmet Requirement",
        "description": "All personnel inside warehouse floors, loading bays, and operational areas must wear safety helmets.",
        "rule_type": "required_object_present",
        "parameters": {
            "zone": "operational_floor",
            "target_class": "person",
            "required_class": "safety-helmet"
        },
        "policy_ref": "Clause 2.1 - Safety Helmet Mandate (Head Protection)"
    },
    {
        "name": "PPE Safety Vest Requirement",
        "description": "High-visibility safety vests mandatory in areas with vehicle or forklift traffic.",
        "rule_type": "required_object_present",
        "parameters": {
            "target_class": "person",
            "required_class": "safety-vest",
            "co_occurring_classes": ["forklift", "vehicle/truck"]
        },
        "policy_ref": "Clause 2.2 - Safety Vest Requirement (High-Visibility Clothing)"
    },
    {
        "name": "Fire Extinguisher Clearance Rule",
        "description": "Radial clearance of 1.0m around fire extinguishers must remain 100% free of obstacles and pallets.",
        "rule_type": "zone_clear",
        "parameters": {
            "target_class": "safety- fire extinguisher",
            "forbidden_classes": ["pallets", "obstacle"],
            "min_clearance_radial_m": 1.0
        },
        "policy_ref": "Clause 3.1 - Fire Extinguisher Clearance & Readiness"
    },
    {
        "name": "Fire Hose Station Access Rule",
        "description": "Clear perimeter of 1.5m in front of fire hose reel stations must be preserved.",
        "rule_type": "zone_clear",
        "parameters": {
            "target_class": "fire-hose",
            "forbidden_classes": ["pallets", "obstacle"],
            "min_clearance_m": 1.5
        },
        "policy_ref": "Clause 3.2 - Fire Hose Reel Station Accessibility"
    },
    {
        "name": "Active Fire Hazard Emergency Rule",
        "description": "Immediate Level 1 emergency. Zero tolerance for uncontrolled fire or flames on site.",
        "rule_type": "forbidden_object_absent",
        "parameters": {
            "forbidden_classes": ["fire"],
            "severity": "Critical"
        },
        "policy_ref": "Clause 3.3 - Active Fire Hazard Detection & Emergency Protocol"
    },
    {
        "name": "Spill Demarcation & Safety Cone Rule",
        "description": "Liquid spills exceeding 0.5L must be cordoned off with high-visibility safety cones within 15 minutes.",
        "rule_type": "required_object_present",
        "parameters": {
            "trigger_class": "spill",
            "required_class": "safety-cone",
            "min_count": 2
        },
        "policy_ref": "Clause 5.1 & 5.2 - Spill Containment & Mandatory Safety Cone Deployment"
    },
    {
        "name": "Forklift Pedestrian Separation Rule",
        "description": "Mandatory minimum 2.5m separation between operating forklifts and pedestrian personnel.",
        "rule_type": "proximity_threshold",
        "parameters": {
            "class_a": "forklift",
            "class_b": "person",
            "min_distance_m": 2.5
        },
        "policy_ref": "Clause 1.2 - Forklift Operation & Pedestrian Separation"
    },
    {
        "name": "Shelf Stocking & Empty Shelf Limit",
        "description": "Empty shelf space must not exceed 15% of shelf area during operating hours.",
        "rule_type": "threshold_limit",
        "parameters": {
            "target_class": "empty-shelf",
            "max_ratio": 0.15
        },
        "policy_ref": "Clause 7.1 - Retail & Warehouse Shelf Stocking (Empty Shelf Protocol)"
    },
    {
        "name": "Industrial Machinery Perimeter Rule",
        "description": "Personnel must maintain safe perimeter and not enter hazardous machinery zones without LOTO permit.",
        "rule_type": "zone_boundary_check",
        "parameters": {
            "hazard_class": "machinery",
            "target_class": "person",
            "zone": "machinery_operating_zone"
        },
        "policy_ref": "Clause 8.1 - Machinery Safety Perimeter & Guarding"
    }
]

def sync_rules():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # Get primary policy ID
    cur.execute("SELECT id FROM policies LIMIT 1;")
    policy_row = cur.fetchone()
    policy_id = policy_row[0] if policy_row else None

    print(f"Syncing {len(RULES)} policy-linked rules to Neon DB...")
    import json
    for r in RULES:
        cur.execute("""
            INSERT INTO rules (name, description, rule_type, parameters, policy_ref, policy_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
        """, (
            r["name"],
            r["description"],
            r["rule_type"],
            json.dumps(r["parameters"]),
            r["policy_ref"],
            policy_id
        ))

    cur.execute("SELECT COUNT(*) FROM rules;")
    total = cur.fetchone()[0]
    print(f"SUCCESS: {total} total compliance rules active in Neon DB.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    sync_rules()

