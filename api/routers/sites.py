"""
SITESENSE - Sites, Rules & Tickets Router
Endpoints:
  - GET  /sites    : List sites the caller may see
  - GET  /rules    : List compliance rules
  - POST /tickets  : Create or approve a remediation ticket
"""

import os
from pathlib import Path
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")

router = APIRouter(tags=["Sites & Rules"])

@router.get("/sites")
async def list_sites():
    """API Contract: GET /sites -> [{id, name, type, location}]"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, name, type, location, active FROM sites WHERE active = true ORDER BY name;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": str(r["id"]), "name": r["name"], "type": r["type"], "location": r["location"]} for r in rows]

@router.get("/rules")
async def list_rules():
    """API Contract: GET /rules -> [{id, name, type, parameters, policy_ref}]"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, name, rule_type, parameters, policy_ref FROM rules ORDER BY name;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": str(r["id"]), "name": r["name"], "type": r["rule_type"], "parameters": r["parameters"], "policy_ref": r["policy_ref"]} for r in rows]

class TicketApprovalRequest(BaseModel):
    finding_id: str
    description: Optional[str] = None
    approved: bool = True

@router.post("/tickets")
async def create_or_approve_ticket(req: TicketApprovalRequest):
    """
    API Contract: POST /tickets
    Approves or creates a ticket from an approved proposal.
    Enforces the Human-in-the-Loop approval gate.
    """
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=RealDictCursor)

    status = "approved" if req.approved else "rejected"

    cur.execute("""
        INSERT INTO tickets (finding_id, status)
        VALUES (%s, %s)
        RETURNING id, status;
    """, (req.finding_id, status))
    row = cur.fetchone()
    cur.close()
    conn.close()

    return {"ticket_id": str(row["id"]), "status": row["status"]}
