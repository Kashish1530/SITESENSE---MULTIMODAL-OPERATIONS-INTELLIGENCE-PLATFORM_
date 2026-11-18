"""
SITESENSE - Remediation Ticket Tool with Approval Gate (Feature 4.8)
Proposes a maintenance or remediation ticket from a failed finding.
Enforces the Human-in-the-Loop approval gate (status is always 'proposed').
"""

from typing import Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from agentic.tools.registry import registry
from agentic.tools.query_database import get_db_url

@registry.register(
    name="raise_ticket",
    description="Propose a remediation ticket from a non-compliant or failed finding. The ticket is held in 'proposed' status and requires human approval before execution.",
    parameters={
        "type": "object",
        "properties": {
            "finding_id": {
                "type": "string",
                "description": "The UUID of the non-compliant finding triggering the ticket."
            },
            "description": {
                "type": "string",
                "description": "Details of the violation, required corrective action, and priority."
            }
        },
        "required": ["finding_id", "description"]
    }
)
def raise_ticket(finding_id: str, description: str) -> Dict[str, Any]:
    db_url = get_db_url()
    if not db_url:
        return {"success": False, "error": "DATABASE_URL not configured."}

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Check if finding exists
        cur.execute("SELECT id, status, rule_id FROM findings WHERE id::text = %s;", (finding_id,))
        finding = cur.fetchone()
        if not finding:
            cur.close()
            conn.close()
            return {"success": False, "error": f"Finding with ID '{finding_id}' not found."}

        # Insert ticket strictly in 'proposed' status (Approval Gate)
        cur.execute("""
            INSERT INTO tickets (finding_id, status)
            VALUES (%s, 'proposed')
            RETURNING id, finding_id, status, created_at;
        """, (finding_id,))
        ticket = cur.fetchone()

        cur.close()
        conn.close()

        return {
            "success": True,
            "ticket_id": str(ticket["id"]),
            "finding_id": str(ticket["finding_id"]),
            "status": "proposed",
            "approval_gate": "HELD: Ticket proposed by Agent. Awaiting manager review and explicit approval in UI before creation.",
            "description": description
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

