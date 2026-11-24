"""
SITESENSE - Automated Compliance & Policy Flagging Engine (Feature 2.7, Flow 1)
Evaluates CV model detections (from uploaded images/videos) against the official Policy Handbook.
Flags non-compliant findings immediately, logs evidence to Neon DB, and proposes remediation tickets.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")

def evaluate_inspection_compliance(inspection_id: str) -> Dict[str, Any]:
    """
    Evaluates all media detections for an inspection against policy rules.
    Writes findings and proposes tickets directly to Neon DB.
    """
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1. Fetch all detections for this inspection
    cur.execute("""
        SELECT 
            d.id AS detection_id,
            d.media_id,
            d.class_name,
            d.bbox,
            d.confidence,
            d.zone,
            d.frame_no,
            m.path AS media_path
        FROM detections d
        JOIN media m ON d.media_id = m.id
        WHERE m.inspection_id::text = %s;
    """, (inspection_id,))
    detections = cur.fetchall()

    if not detections:
        cur.close()
        conn.close()
        return {
            "inspection_id": inspection_id,
            "status": "no_detections",
            "message": "No visual detections recorded for this inspection."
        }

    # 2. Fetch all active policy-linked compliance rules
    cur.execute("""
        SELECT id, name, rule_type, parameters, policy_ref
        FROM rules;
    """)
    rules = cur.fetchall()

    detected_classes = [d["class_name"].lower() for d in detections]
    detections_by_class: Dict[str, List[Dict[str, Any]]] = {}
    for d in detections:
        cls = d["class_name"].lower()
        detections_by_class.setdefault(cls, []).append(d)

    findings_created = []
    tickets_proposed = []

    # 3. Evaluate each rule against detections
    for rule in rules:
        rule_id = str(rule["id"])
        rule_name = rule["name"]
        rule_type = rule["rule_type"]
        params = rule["parameters"] if isinstance(rule["parameters"], dict) else json.loads(rule["parameters"] or "{}")
        policy_ref = rule["policy_ref"]

        status = "pass"
        evidence_ids = []
        violation_reason = None

        # --- Rule Check 1: Walkway & Exit Obstruction ---
        if rule_name in ["Walkway Obstruction Rule", "Walkway Clearance Rule", "Fire Exit Clearance Rule"]:
            forbidden = params.get("forbidden_classes", ["pallets", "obstacle"])
            for fc in forbidden:
                for d in detections_by_class.get(fc, []):
                    zone = (d.get("zone") or "").lower()
                    if "walkway" in zone or "exit" in zone or not zone:
                        status = "fail"
                        evidence_ids.append(str(d["detection_id"]))
                        violation_reason = f"Prohibited object '{fc}' detected in transit zone: {d['zone']} (Confidence: {float(d['confidence']):.2f})"

        # --- Rule Check 2: PPE Helmet Requirement ---
        elif "Helmet" in rule_name or "Hard Hat" in rule_name:
            if "no_hardhat" in detections_by_class:
                status = "fail"
                evidence_ids = [str(d["detection_id"]) for d in detections_by_class["no_hardhat"]]
                violation_reason = f"Explicit PPE violation: {len(evidence_ids)} worker(s) detected without mandatory hard hat."
            else:
                persons = detections_by_class.get("person", [])
                helmets = detections_by_class.get("safety-helmet", []) + detections_by_class.get("hardhat", [])
                if persons and len(helmets) < len(persons):
                    status = "fail"
                    evidence_ids = [str(p["detection_id"]) for p in persons]
                    violation_reason = f"{len(persons)} person(s) detected, but only {len(helmets)} safety helmet(s) identified."

        # --- Rule Check 3: PPE Vest Requirement ---
        elif "Vest" in rule_name:
            if "no_safety_vest" in detections_by_class:
                status = "fail"
                evidence_ids = [str(d["detection_id"]) for d in detections_by_class["no_safety_vest"]]
                violation_reason = f"Explicit PPE violation: {len(evidence_ids)} worker(s) detected without required high-vis vest."
            else:
                persons = detections_by_class.get("person", [])
                vests = detections_by_class.get("safety-vest", []) + detections_by_class.get("safety_vest", [])
                has_heavy_traffic = bool(detections_by_class.get("forklift") or detections_by_class.get("vehicle/truck") or detections_by_class.get("truck") or detections_by_class.get("crane") or detections_by_class.get("excavator"))
                if persons and has_heavy_traffic and len(vests) < len(persons):
                    status = "fail"
                    evidence_ids = [str(p["detection_id"]) for p in persons]
                    violation_reason = f"Vehicle/machinery traffic present, but {len(persons) - len(vests)} person(s) lack required high-vis safety vest."

        # --- Rule Check 4: Fire Hazard ---
        elif "Active Fire" in rule_name or "fire" in params.get("forbidden_classes", []):
            if "fire" in detections_by_class:
                status = "fail"
                evidence_ids = [str(d["detection_id"]) for d in detections_by_class["fire"]]
                violation_reason = "CRITICAL EMERGENCY: Active fire/flame detected on site!"

        # --- Rule Check 5: Spill without Safety Cones ---
        elif "Spill" in rule_name:
            if "spill" in detections_by_class:
                cones = detections_by_class.get("safety-cone", [])
                if len(cones) < 2:
                    status = "fail"
                    evidence_ids = [str(d["detection_id"]) for d in detections_by_class["spill"]]
                    violation_reason = f"Liquid spill detected without mandatory cordon (found {len(cones)} safety cones; 2 required)."

        # --- Rule Check 6: Empty Shelf Limit ---
        elif "Empty Shelf" in rule_name:
            empty_shelves = detections_by_class.get("empty-shelf", [])
            if len(empty_shelves) >= 2:
                status = "fail"
                evidence_ids = [str(d["detection_id"]) for d in empty_shelves]
                violation_reason = f"High density of empty shelves ({len(empty_shelves)} sections) detected exceeding 15% shelf threshold."

        # --- Rule Check 7: Forklift Separation ---
        elif "Forklift" in rule_name:
            if "forklift" in detections_by_class and "person" in detections_by_class:
                status = "fail"
                evidence_ids = [str(d["detection_id"]) for d in detections_by_class["forklift"]] + [str(d["detection_id"]) for d in detections_by_class["person"]]
                violation_reason = "Pedestrian and operating forklift detected in shared operational zone."

        # Only record findings that either explicitly pass or fail
        if evidence_ids or status == "fail":
            # 4. Insert Finding into Neon DB
            cur.execute("""
                INSERT INTO findings (inspection_id, rule_id, status, evidence_ids)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (
                inspection_id,
                rule_id,
                status,
                json.dumps(evidence_ids)
            ))
            finding_id = str(cur.fetchone()["id"])

            findings_created.append({
                "finding_id": finding_id,
                "rule": rule_name,
                "policy_ref": policy_ref,
                "status": status,
                "evidence_ids": evidence_ids,
                "reason": violation_reason
            })

            # 5. If failed: Immediately propose a remediation ticket
            if status == "fail":
                cur.execute("""
                    INSERT INTO tickets (finding_id, status)
                    VALUES (%s, 'proposed')
                    RETURNING id;
                """, (finding_id,))
                ticket_id = str(cur.fetchone()["id"])
                tickets_proposed.append({
                    "ticket_id": ticket_id,
                    "finding_id": finding_id,
                    "rule": rule_name,
                    "policy_ref": policy_ref,
                    "status": "proposed (awaiting manager approval)"
                })

    # Update inspection status
    final_status = "completed"
    cur.execute("UPDATE inspections SET status = %s WHERE id::text = %s;", (final_status, inspection_id))

    cur.close()
    conn.close()

    failures = [f for f in findings_created if f["status"] == "fail"]
    return {
        "inspection_id": inspection_id,
        "total_rules_evaluated": len(findings_created),
        "violations_flagged": len(failures),
        "findings": findings_created,
        "tickets_proposed": tickets_proposed,
        "summary": "COMPLIANCE VIOLATIONS FLAGGED IMMEDIATELY" if failures else "ALL CHECKS PASSED"
    }

