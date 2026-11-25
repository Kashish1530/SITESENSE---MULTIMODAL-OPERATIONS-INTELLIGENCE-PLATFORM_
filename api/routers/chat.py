"""
SITESENSE - Conversational Agent Router (Feature 5.3, 4.2, 4.11)
Endpoints:
  - POST /chat               : Ask the Agent a question (returns answer, citations, tools)
  - GET  /chat/{run_id}/trace : Retrieve full audit trail & telemetry for a run from Neon DB
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from agentic.core import SiteSenseAgent

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")

router = APIRouter(tags=["Agent Chat"])

class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = "default_session"
    user_id: Optional[str] = None
    image_url: Optional[str] = None

@router.post("/chat")
async def chat_with_agent(req: ChatRequest):
    """
    API Contract: POST /chat
    Invokes the SiteSense Reason-Act-Observe agent loop.
    Returns the answer with citations, evidence links, and tool invocation steps.
    Logs run directly to Neon DB.
    """
    agent = SiteSenseAgent()
    has_image = bool(req.image_url)

    result = agent.run(
        question=req.question,
        session_id=req.session_id or "default_session",
        user_id=req.user_id,
        has_image=has_image
    )

    return {
        "answer": result["answer"],
        "route": result["route"],
        "audit_run_id": result["audit_run_id"],
        "tools_called": result["tools_called"],
        "telemetry": {
            "tokens": result["tokens"],
            "cost_usd": result["cost"],
            "latency_sec": result["latency"]
        }
    }

@router.get("/chat/{run_id}/trace")
async def get_agent_trace(run_id: str):
    """
    API Contract: GET /chat/{run_id}/trace
    Returns {route, tools[], tokens, cost, latency} from Neon DB.
    """
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT id, user_id, question, route, tools_called, tokens, cost, latency, created_at
        FROM agent_runs
        WHERE id::text = %s;
    """, (run_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "RUN_NOT_FOUND", "message": f"Agent run '{run_id}' not found."}}
        )

    return {
        "run_id": str(row["id"]),
        "question": row["question"],
        "route": row["route"],
        "tools": row["tools_called"],
        "tokens": row["tokens"],
        "cost": float(row["cost"]) if row["cost"] is not None else 0.0,
        "latency": float(row["latency"]) if row["latency"] is not None else 0.0,
        "timestamp": str(row["created_at"])
    }
