"""
SITESENSE - Safe Read-Only Database Query Tool (Feature 4.6)
Converts or validates natural SQL queries and executes strictly read-only statements on Neon DB.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List
import psycopg2
from psycopg2.extras import RealDictCursor
from agentic.tools.registry import registry

def get_db_url() -> str:
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("DATABASE_URL="):
                    return line.strip().split("DATABASE_URL=", 1)[1].strip('"').strip("'")
    return os.getenv("DATABASE_URL", "")

FORBIDDEN_KEYWORDS = [
    "drop", "delete", "update", "insert", "alter", "truncate", "create", 
    "grant", "revoke", "replace", "vacuum", "reindex", "execute", "call"
]

def validate_read_only_sql(sql: str) -> bool:
    clean_sql = re.sub(r"--.*", "", sql).strip().lower()
    clean_sql = re.sub(r"/\*.*?\*/", "", clean_sql, flags=re.DOTALL).strip()
    
    # Must start with SELECT or WITH
    if not (clean_sql.startswith("select") or clean_sql.startswith("with")):
        return False

    for word in FORBIDDEN_KEYWORDS:
        if re.search(r"\b" + word + r"\b", clean_sql):
            return False
    return True

@registry.register(
    name="commentary",
    description="Internal assistant scratchpad and intermediate query execution.",
    parameters={
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "Optional SQL query to execute if testing a hypothesis."
            },
            "thought": {
                "type": "string",
                "description": "Reasoning commentary."
            }
        }
    }
)
def commentary(sql: str = None, thought: str = None) -> Dict[str, Any]:
    if sql and validate_read_only_sql(sql):
        return query_database(sql)
    return {"status": "noted", "message": "Observation recorded."}

@registry.register(
    name="query_database",
    description="Execute a validated read-only SQL query against the Neon PostgreSQL database (inspections, sites, findings, detections, extractions, rules, tickets). Only SELECT queries are permitted.",
    parameters={
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "The SQL query to execute. Must begin with SELECT and contain only read-only statements."
            }
        },
        "required": ["sql"]
    }
)
def query_database(sql: str) -> Dict[str, Any]:
    if not validate_read_only_sql(sql):
        return {
            "success": False,
            "error": "Security Guardrail Violation: Destructive or non-SELECT SQL statements are strictly prohibited.",
            "attempted_sql": sql
        }

    db_url = get_db_url()
    if not db_url:
        return {"success": False, "error": "DATABASE_URL not configured."}

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        formatted_rows = []
        for r in rows[:25]:  # Limit rows returned to model context
            formatted_rows.append({k: str(v) for k, v in r.items()})

        return {
            "success": True,
            "row_count": len(rows),
            "rows": formatted_rows,
            "executed_sql": sql
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"SQL Execution Error: {str(e)}",
            "attempted_sql": sql
        }
