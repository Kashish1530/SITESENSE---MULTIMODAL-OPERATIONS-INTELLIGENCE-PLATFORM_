"""
Remediation ticket tool with approval gate.

The agent proposes corrective maintenance tickets in 'proposed' status.
Tickets require explicit human sign-off via approve_ticket() before activation.
"""

from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from agentic.tools.registry import registry
from agentic.tools.query_database import get_db_url

@registry.register(
    name="raise_ticket", 
    description="Propose a remediation ticket from a non-compliant or failed finding. The ticket is held in 'proposed' status and requires human approval before creation.",
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
    """
    Agent tool: proposes a ticket.
    Strictly holds ticket in 'proposed' status to enforce human-in-the-loop approval.
    """
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

        # Insert ticket strictly in 'proposed' status (Human Approval Gate)
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
            "approval_gate": "HELD: Ticket proposed by Agent. Awaiting manager review and explicit human approval before creation.",
            "description": description
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def approve_ticket(ticket_id: str, approver_user_id: str) -> Dict[str, Any]:
    """
    Human-in-the-loop approval function:
    Transitions a proposed ticket to 'approved', recording the human approver's user ID.
    Acceptance Criteria: The approval and approver are both recorded.
    """
    db_url = get_db_url()
    if not db_url:
        return {"success": False, "error": "DATABASE_URL not configured."}

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verify approver exists in users table
        cur.execute("SELECT id, name, role FROM users WHERE id::text = %s;", (approver_user_id,))
        approver = cur.fetchone()
        if not approver:
            cur.close()
            conn.close()
            return {"success": False, "error": f"Approver with user ID '{approver_user_id}' does not exist."}

        # Update ticket status to 'approved' and assign approver
        cur.execute("""
            UPDATE tickets
            SET status = 'approved',
                approved_by = %s,
                approved_at = CURRENT_TIMESTAMP
            WHERE id::text = %s
            RETURNING id, finding_id, status, approved_by, approved_at, created_at;
        """, (approver_user_id, ticket_id))
        updated = cur.fetchone()

        cur.close()
        conn.close()

        if not updated:
            return {"success": False, "error": f"Ticket '{ticket_id}' not found."}

        return {
            "success": True,
            "ticket_id": str(updated["id"]),
            "status": updated["status"],
            "approver_id": str(updated["approved_by"]),
            "approved_at": str(updated["approved_at"]),
            "approver_name": approver["name"],
            "approver_role": approver["role"],
            "message": "Ticket successfully approved by authorized human manager."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
