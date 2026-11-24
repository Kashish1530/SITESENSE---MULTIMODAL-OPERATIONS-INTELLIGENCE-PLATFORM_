"""
Database query tool for the SiteSense agent.

Validates that incoming queries are strictly read-only (SELECT / WITH)
and executes them against the PostgreSQL instance with safety guards.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

from agentic.tools.registry import registry


def get_db_url() -> str:
    """Reads the DATABASE_URL connection string from .env or environment."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("DATABASE_URL="):
                    return line.strip().split("DATABASE_URL=", 1)[1].strip('"').strip("'")
    return os.getenv("DATABASE_URL", "")


# Keywords that cannot appear as executable statements
FORBIDDEN_KEYWORDS = [
    "drop", "delete", "update", "insert", "alter", "truncate", "create", 
    "grant", "revoke", "replace", "vacuum", "reindex", "execute", "call"
]


def validate_read_only_sql(sql: str) -> bool:
    """
    Checks that the SQL statement is strictly read-only:
    - Strips line comments and block comments
    - Enforces starting with SELECT or WITH
    - Rejects DDL and destructive DML keywords
    """
    clean = re.sub(r"--.*", "", sql).strip().lower()
    clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL).strip()
    
    # Must start with SELECT or WITH (for CTEs)
    if not (clean.startswith("select") or clean.startswith("with")):
        return False

    for word in FORBIDDEN_KEYWORDS:
        if re.search(r"\b" + word + r"\b", clean):
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
    """Helper tool for intermediate reasoning and test queries."""
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
    """Runs a read-only query and formats rows as string dicts for LLM consumption."""
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
        with psycopg2.connect(db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()

        # Format and cap rows to prevent overflowing model context window
        formatted = [{k: str(v) for k, v in row.items()} for row in rows[:25]]

        return {
            "success": True,
            "row_count": len(rows),
            "rows": formatted,
            "executed_sql": sql
        }
    except Exception as err:
        return {
            "success": False,
            "error": f"SQL Execution Error: {str(err)}",
            "attempted_sql": sql
        }
