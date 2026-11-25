"""
Conversation and persistent site memory for the SiteSense agent.

Supports two tiers:
1. In-memory short-term session window for multi-turn chat dialogues.
2. PostgreSQL-backed persistent site memory (in the 'site_memory' table)
   that stores ongoing facility notes across server restarts.
"""

import os
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

from agentic.tools.query_database import get_db_url


class ConversationMemory:
    """Manages active session dialogues and persistent per-site metadata."""

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}
        self._init_db_table()

    def _init_db_table(self):
        """Ensures the site_memory table exists in Postgres."""
        db_url = get_db_url()
        if not db_url:
            return
        try:
            with psycopg2.connect(db_url) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS site_memory (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            site_id UUID REFERENCES sites(id) ON DELETE CASCADE,
                            site_name VARCHAR(255),
                            key VARCHAR(100) NOT NULL,
                            value TEXT NOT NULL,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            CONSTRAINT unique_site_key UNIQUE(site_id, key)
                        );
                    """)
        except Exception as err:
            print(f"[Memory] Failed to verify site_memory table: {err}")

    # --- Short-term in-session history ---

    def add_message(self, session_id: str, role: str, content: str):
        """Appends a new turn to the in-memory session buffer."""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append({"role": role, "content": content})
        
        # Keep within the max turn window (2 messages per turn: user + assistant)
        max_messages = self.max_turns * 2
        if len(self.sessions[session_id]) > max_messages:
            self.sessions[session_id] = self.sessions[session_id][-max_messages:]

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Returns shallow copy of session history."""
        return list(self.sessions.get(session_id, []))

    def clear_session(self, session_id: str):
        """Clears temporary conversation buffer for a given session."""
        self.sessions.pop(session_id, None)

    # --- Persistent per-site storage (Neon DB) ---

    def set_site_context(self, site_identifier: str, key: str, value: str) -> bool:
        """Stores or updates persistent key-value context for a facility."""
        db_url = get_db_url()
        if not db_url:
            return False

        try:
            with psycopg2.connect(db_url) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    # Look up site_id UUID from name or ID string
                    cur.execute("""
                        SELECT id FROM sites WHERE name ILIKE %s OR id::text = %s LIMIT 1;
                    """, (f"%{site_identifier}%", site_identifier))
                    row = cur.fetchone()
                    site_id = row[0] if row else None

                    cur.execute("""
                        INSERT INTO site_memory (site_id, site_name, key, value, updated_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (site_id, key)
                        DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP;
                    """, (site_id, site_identifier, key, value))
            return True
        except Exception as err:
            print(f"[Memory] Could not persist site memory: {err}")
            return False

    def get_site_context(self, site_identifier: str) -> Dict[str, str]:
        """Returns all stored key-value attributes for a site."""
        db_url = get_db_url()
        if not db_url:
            return {}

        try:
            with psycopg2.connect(db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT key, value FROM site_memory
                        WHERE site_name ILIKE %s OR site_id::text = %s
                        ORDER BY updated_at DESC;
                    """, (f"%{site_identifier}%", site_identifier))
                    rows = cur.fetchall()
                    return {r["key"]: r["value"] for r in rows}
        except Exception as err:
            print(f"[Memory] Could not load site memory: {err}")
            return {}

    # Backward-compatible aliases
    set_site_memory = set_site_context
    get_all_site_memory = get_site_context


# Shared singleton instance
memory = ConversationMemory()
