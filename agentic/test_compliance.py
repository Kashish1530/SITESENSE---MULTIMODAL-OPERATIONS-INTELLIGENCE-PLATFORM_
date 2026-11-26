"""
SITESENSE - Test Compliance Flagging Engine
Demonstrates automated rule checking against uploaded media detections.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
from dotenv import load_dotenv
from agentic.compliance_engine import evaluate_inspection_compliance

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()
cur.execute("""
    SELECT i.id 
    FROM inspections i 
    JOIN media m ON m.inspection_id = i.id 
    JOIN detections d ON d.media_id = m.id 
    LIMIT 1;
""")
row = cur.fetchone()
if not row:
    cur.execute("SELECT id FROM inspections LIMIT 1;")
    row = cur.fetchone()
conn.close()

if not row:
    print("No inspection found to test.")
    exit(0)

insp_id = str(row[0])
print(f"Running Automated Compliance Engine on Inspection: {insp_id}...")
result = evaluate_inspection_compliance(insp_id)

print("\n" + "=" * 80)
if "summary" in result:
    print(f"RESULT: {result['summary']}")
    print(f"Violations Flagged: {result['violations_flagged']}")
    print("=" * 80)
    print("\nFindings Created:")
    for f in result.get("findings", []):
        status_tag = f"[{f['status'].upper()}]"
        print(f" {status_tag} {f['rule']}")
else:
    print(f"STATUS: {result.get('status')} - {result.get('message')}")
    print("=" * 80)
    print(f"     Policy Clause: {f['policy_ref']}")
    if f.get("reason"):
        print(f"     Violation Reason: {f['reason']}")
    print(f"     Evidence Detection IDs: {f['evidence_ids']}")

print(f"\nRemediation Tickets Proposed (Held at Approval Gate): {len(result['tickets_proposed'])}")
for t in result["tickets_proposed"]:
    print(f" - Ticket ID: {t['ticket_id']} | Rule: {t['rule']} | Status: {t['status']}")
