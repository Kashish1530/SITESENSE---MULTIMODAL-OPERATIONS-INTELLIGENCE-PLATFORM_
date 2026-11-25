"""
SITESENSE - Seed script with initial demo data
Populates sample records for all 11 core tables to verify constraints and relationships.
"""

import os
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

def load_env(env_path: Path):
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

current_dir = Path(__file__).resolve().parent
load_env(current_dir / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

def seed():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print("Seeding sample data into Neon DB...")

    # 1. Sites
    cur.execute("""
        INSERT INTO sites (name, type, location, active)
        VALUES 
            ('Site 7 - Central Distribution Hub', 'warehouse', 'Sector 18, Gurugram, India', true),
            ('Site 12 - Retail Superstore', 'retail store', 'Connaught Place, New Delhi, India', true)
        ON CONFLICT DO NOTHING
        RETURNING id, name;
    """)
    sites = cur.fetchall()
    if not sites:
        cur.execute("SELECT id, name FROM sites LIMIT 2;")
        sites = cur.fetchall()
    site_id = sites[0][0]
    print(f" - Site: {sites[0][1]} ({site_id})")

    # 2. Users (all 4 roles: admin, manager, field, reviewer)
    cur.execute("""
        INSERT INTO users (name, email, role)
        VALUES 
            ('Admin User', 'admin@sitesense.io', 'admin'),
            ('Operations Manager', 'manager@sitesense.io', 'manager'),
            ('Field Supervisor 1', 'field1@sitesense.io', 'field'),
            ('Compliance Reviewer 1', 'reviewer1@sitesense.io', 'reviewer')
        ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
        RETURNING id, email, role;
    """)
    users = {row[2]: row[0] for row in cur.fetchall()}
    if len(users) < 4:
        cur.execute("SELECT role, id FROM users;")
        users = {row[0]: row[1] for row in cur.fetchall()}
    print(f" - Users created/loaded for roles: {list(users.keys())}")

    # Clean up prior seed inspection and test policy to keep re-runs idempotent
    cur.execute("DELETE FROM inspections WHERE job_id = 'job_inspection_001_seed';")
    cur.execute("DELETE FROM policies WHERE title = 'Occupational Health, Safety & Storage Handbook';")
    cur.execute("DELETE FROM agent_runs WHERE question LIKE 'Did Site 7 pass the walkway clearance rule%';")

    # 3. Policy
    cur.execute("""
        INSERT INTO policies (title, version, source_file, effective_date)
        VALUES ('Occupational Health, Safety & Storage Handbook', '2026.Q1', 'policies/ohs_guidelines_2026.pdf', '2026-01-01')
        RETURNING id, title;
    """)
    policy = cur.fetchone()
    policy_id = policy[0]
    print(f" - Policy: {policy[1]} ({policy_id})")

    # 4. Rules
    cur.execute(f"""
        INSERT INTO rules (name, description, rule_type, parameters, policy_ref, policy_id)
        VALUES 
            (
                'Walkway Clearance Rule', 
                'Main transit walkways and fire exits must maintain at least 1.2m unobstructed clearance.', 
                'zone_clear', 
                '{{"zone": "main_walkway", "min_clearance_meters": 1.2, "forbidden_classes": ["pallet", "box", "debris"]}}'::jsonb, 
                'Clause 4.2 - Emergency Pathways', 
                '{policy_id}'
            ),
            (
                'PPE Helmet Requirement', 
                'All personnel within the warehouse operational zone must wear certified safety helmets.', 
                'required_object_present', 
                '{{"required_class": "safety_helmet", "target_class": "person", "zone": "operational_floor"}}'::jsonb, 
                'Clause 2.1 - Personal Protective Equipment', 
                '{policy_id}'
            )
        RETURNING id, name;
    """)
    rules = cur.fetchall()
    rule_id_walkway = rules[0][0]
    rule_id_ppe = rules[1][0]
    print(f" - Rules created: {len(rules)}")

    # 5. Inspection
    cur.execute(f"""
        INSERT INTO inspections (site_id, user_id, status, job_id)
        VALUES ('{site_id}', '{users.get("field")}', 'completed', 'job_inspection_001_seed')
        ON CONFLICT (job_id) DO UPDATE SET status = EXCLUDED.status
        RETURNING id;
    """)
    inspection_id = cur.fetchone()[0]
    print(f" - Inspection created/loaded: {inspection_id}")

    # 6. Media
    cur.execute(f"""
        INSERT INTO media (inspection_id, type, path, metadata)
        VALUES 
            ('{inspection_id}', 'image', 'uploads/inspections/001/walkway_camera1.jpg', '{{"resolution": "1920x1080", "gps": {{"lat": 28.4595, "lng": 77.0266}}, "device": "iPhone 15 Pro"}}'::jsonb),
            ('{inspection_id}', 'doc', 'uploads/inspections/001/delivery_note_1042.pdf', '{{"pages": 1, "format": "pdf"}}'::jsonb)
        RETURNING id, type;
    """)
    media_records = cur.fetchall()
    image_media_id = media_records[0][0]
    doc_media_id = media_records[1][0]
    print(f" - Media items created: image={image_media_id}, doc={doc_media_id}")

    # 7. Detection (CV Finding evidence)
    cur.execute(f"""
        INSERT INTO detections (media_id, class_name, bbox, confidence, zone, frame_no)
        VALUES 
            ('{image_media_id}', 'pallet', '[350, 420, 680, 750]'::jsonb, 0.9420, 'main_walkway', NULL),
            ('{image_media_id}', 'person', '[120, 200, 310, 890]'::jsonb, 0.8850, 'main_walkway', NULL)
        RETURNING id;
    """)
    detection_ids = [row[0] for row in cur.fetchall()]
    print(f" - Detections recorded: {len(detection_ids)}")

    # 8. Extractions (Document fields)
    cur.execute(f"""
        INSERT INTO extractions (media_id, field_name, value, confidence, reviewed_by)
        VALUES 
            ('{doc_media_id}', 'vendor_name', 'Acme Logistics Ltd', 0.9850, NULL),
            ('{doc_media_id}', 'invoice_total', '₹45,200', 0.8200, NULL)
        RETURNING id;
    """)
    extractions = cur.fetchall()
    print(f" - Extractions recorded: {len(extractions)}")

    # 9. Findings
    cur.execute(f"""
        INSERT INTO findings (inspection_id, rule_id, status, evidence_ids)
        VALUES 
            ('{inspection_id}', '{rule_id_walkway}', 'fail', '["{detection_ids[0]}"]'::jsonb)
        RETURNING id;
    """)
    finding_id = cur.fetchone()[0]
    print(f" - Finding created: {finding_id} (Status: fail)")

    # 10. Ticket (Proposed remediation action)
    cur.execute(f"""
        INSERT INTO tickets (finding_id, status, created_by, approved_by)
        VALUES ('{finding_id}', 'proposed', '{users.get("field")}', NULL)
        RETURNING id;
    """)
    ticket_id = cur.fetchone()[0]
    print(f" - Ticket proposed: {ticket_id}")

    # 11. Agent Run (Audit trail)
    cur.execute(f"""
        INSERT INTO agent_runs (user_id, question, route, tools_called, tokens, cost, latency)
        VALUES (
            '{users.get("manager")}', 
            'Did Site 7 pass the walkway clearance rule this week, and show me the evidence.', 
            'vision_and_policy', 
            '[{{"tool": "search_policies", "clause": "4.2"}}, {{"tool": "query_database", "target": "findings"}}]'::jsonb, 
            650, 
            0.001950, 
            1.450
        )
        RETURNING id;
    """)
    agent_run_id = cur.fetchone()[0]
    print(f" - Agent run logged: {agent_run_id}")

    cur.close()
    conn.close()
    print("\nSeed completed successfully! All tables contain valid test data.")

if __name__ == "__main__":
    seed()

