"""
SITESENSE - Report Generation Tool (Feature 4.7)
Assembles structured inspection findings and evidence into a formatted compliance report.
"""

from typing import Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from agentic.tools.registry import registry
from agentic.tools.query_database import get_db_url

@registry.register(
    name="generate_report",
    description="Generate a comprehensive inspection compliance report for a site inspection with linked evidence and rule evaluations.",
    parameters={
        "type": "object",
        "properties": {
            "inspection_id": {
                "type": "string",
                "description": "The UUID of the completed inspection to generate a report for."
            }
        },
        "required": ["inspection_id"]
    }
)
def generate_report(inspection_id: str) -> Dict[str, Any]:
    db_url = get_db_url()
    if not db_url:
        return {"success": False, "error": "DATABASE_URL not configured."}

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 1. Inspection details
        cur.execute("""
            SELECT i.id, i.created_at, i.status, s.name AS site_name, s.location, u.name AS inspector
            FROM inspections i
            JOIN sites s ON i.site_id = s.id
            LEFT JOIN users u ON i.user_id = u.id
            WHERE i.id::text = %s;
        """, (inspection_id,))
        insp = cur.fetchone()
        if not insp:
            cur.close()
            conn.close()
            return {"success": False, "error": f"Inspection '{inspection_id}' not found."}

        # 2. Findings & Rules
        cur.execute("""
            SELECT f.id AS finding_id, f.status, f.evidence_ids, r.name AS rule_name, r.policy_ref, r.description
            FROM findings f
            JOIN rules r ON f.rule_id = r.id
            WHERE f.inspection_id::text = %s;
        """, (inspection_id,))
        findings = cur.fetchall()

        cur.close()
        conn.close()

        total = len(findings)
        passed = sum(1 for f in findings if f["status"] == "pass")
        failed = sum(1 for f in findings if f["status"] == "fail")
        reviews = sum(1 for f in findings if f["status"] == "review")

        pass_rate = f"{(passed / total * 100):.1f}%" if total > 0 else "N/A"

        return {
            "success": True,
            "report_id": f"REP-{inspection_id[:8].upper()}",
            "site": insp["site_name"],
            "location": insp["location"],
            "inspector": insp["inspector"],
            "inspection_date": str(insp["created_at"]),
            "summary": {
                "total_checks": total,
                "passed": passed,
                "failed": failed,
                "needs_review": reviews,
                "compliance_score": pass_rate
            },
            "findings_detail": findings,
            "download_url": f"/reports/{inspection_id}?format=pdf"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

