"""
violation_db.py
SQLite-backed Violation Lifecycle Manager for SiteSense Member 2.

Tables:
  violations  — Every unique HIGH/CRITICAL spatial violation detected
  resolutions — Proof-of-resolution records tied to a violation

Workflow:
  1. After video analysis  → insert_violation()
  2. User resolves issue   → resolve_violation() + uploads photo
  3. Any query             → get_active_violations() / get_resolved_violations()
  4. Weekly reporting      → get_weekly_summary()
  5. GenAI agent tool      → get_violation_by_id()
"""

import sqlite3
import os
import uuid
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

DB_PATH = os.path.abspath("outputs/sitesense_violations.db")


def _get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # access columns by name
    return conn


def init_db():
    """Create tables if they don't already exist."""
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id                  TEXT PRIMARY KEY,
            event_id            TEXT,
            site_id             TEXT,
            zone_id             TEXT,
            zone_name           TEXT,
            event_type          TEXT,
            severity            TEXT,
            class_name          TEXT,
            track_id            INTEGER,
            dwell_time          REAL,
            timestamp           REAL,
            video_name          TEXT,
            week_number         INTEGER,
            evidence_frame_path TEXT,
            status              TEXT DEFAULT 'ACTIVE',
            created_at          TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS resolutions (
            id                  TEXT PRIMARY KEY,
            violation_id        TEXT REFERENCES violations(id),
            resolved_by         TEXT,
            resolution_photo_path TEXT,
            resolution_note     TEXT,
            resolved_at         TEXT,
            week_number         INTEGER
        )
    """)

    conn.commit()
    conn.close()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _week_number() -> int:
    return datetime.now(tz=timezone.utc).isocalendar()[1]


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ── Write Operations ──────────────────────────────────────────────────────────

def insert_violation(
    event: Dict[str, Any],
    evidence_path: Optional[str] = None,
    video_name: str = ""
) -> str:
    """
    Persist a unique spatial violation event into the DB.
    Returns the new violation UUID.
    Deduplicates by (event_type, track_id, zone_id, site_id).
    """
    init_db()
    conn = _get_connection()
    cur = conn.cursor()

    site_id  = event.get("site_id", "SITE_01")
    zone_id  = event.get("zone_id", "")
    track_id = event.get("target", {}).get("track_id", -1)
    ev_type  = event.get("event_type", "")

    # Deduplicate: one record per (site, zone, track, type) lifecycle
    cur.execute("""
        SELECT id FROM violations
        WHERE site_id=? AND zone_id=? AND track_id=? AND event_type=? AND status='ACTIVE'
    """, (site_id, zone_id, track_id, ev_type))
    existing = cur.fetchone()
    if existing:
        conn.close()
        return existing["id"]

    new_id = str(uuid.uuid4())
    ts     = event.get("temporal", {}).get("current_timestamp", 0.0)
    dwell  = event.get("temporal", {}).get("dwell_time_seconds", 0.0)

    cur.execute("""
        INSERT INTO violations
        (id, event_id, site_id, zone_id, zone_name, event_type, severity,
         class_name, track_id, dwell_time, timestamp, video_name, week_number,
         evidence_frame_path, status, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        new_id,
        event.get("event_id", ""),
        site_id,
        zone_id,
        event.get("zone_name", ""),
        ev_type,
        event.get("severity", "HIGH"),
        event.get("target", {}).get("class_name", ""),
        track_id,
        dwell,
        ts,
        video_name,
        _week_number(),
        evidence_path or "",
        "ACTIVE",
        _now_iso()
    ))

    conn.commit()
    conn.close()
    return new_id


def resolve_violation(
    violation_id: str,
    resolved_by: str = "site_supervisor",
    resolution_photo_path: Optional[str] = None,
    resolution_note: str = ""
) -> bool:
    """
    Mark a violation as RESOLVED and store proof record.
    Returns True on success.
    """
    init_db()
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM violations WHERE id=?", (violation_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False

    # Update violation status
    cur.execute("UPDATE violations SET status='RESOLVED' WHERE id=?", (violation_id,))

    # Insert resolution record
    res_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO resolutions
        (id, violation_id, resolved_by, resolution_photo_path, resolution_note, resolved_at, week_number)
        VALUES (?,?,?,?,?,?,?)
    """, (
        res_id,
        violation_id,
        resolved_by,
        resolution_photo_path or "",
        resolution_note,
        _now_iso(),
        _week_number()
    ))

    conn.commit()
    conn.close()
    return True


# ── Read Operations ───────────────────────────────────────────────────────────

def get_active_violations(site_id: Optional[str] = None, zone_id: Optional[str] = None) -> List[Dict]:
    init_db()
    conn = _get_connection()
    cur = conn.cursor()
    q = "SELECT * FROM violations WHERE status='ACTIVE'"
    params: list = []
    if site_id:
        q += " AND site_id=?"
        params.append(site_id)
    if zone_id:
        q += " AND zone_id=?"
        params.append(zone_id)
    q += " ORDER BY created_at DESC"
    cur.execute(q, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_resolved_violations(site_id: Optional[str] = None, week: Optional[int] = None) -> List[Dict]:
    init_db()
    conn = _get_connection()
    cur = conn.cursor()
    q = """
        SELECT v.*, r.resolved_by, r.resolution_photo_path, r.resolution_note, r.resolved_at
        FROM violations v
        LEFT JOIN resolutions r ON r.violation_id = v.id
        WHERE v.status='RESOLVED'
    """
    params: list = []
    if site_id:
        q += " AND v.site_id=?"
        params.append(site_id)
    if week:
        q += " AND v.week_number=?"
        params.append(week)
    q += " ORDER BY r.resolved_at DESC"
    cur.execute(q, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_violation_by_id(violation_id: str) -> Optional[Dict]:
    init_db()
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT v.*, r.resolved_by, r.resolution_photo_path, r.resolution_note, r.resolved_at
        FROM violations v
        LEFT JOIN resolutions r ON r.violation_id = v.id
        WHERE v.id=?
    """, (violation_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_weekly_summary(site_id: Optional[str] = None) -> List[Dict]:
    """Returns per-week counts of ACTIVE vs RESOLVED violations."""
    init_db()
    conn = _get_connection()
    cur = conn.cursor()
    q = """
        SELECT week_number,
               COUNT(*) AS total,
               SUM(CASE WHEN status='ACTIVE'   THEN 1 ELSE 0 END) AS active,
               SUM(CASE WHEN status='RESOLVED' THEN 1 ELSE 0 END) AS resolved
        FROM violations
    """
    params: list = []
    if site_id:
        q += " WHERE site_id=?"
        params.append(site_id)
    q += " GROUP BY week_number ORDER BY week_number"
    cur.execute(q, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_all_violations_count() -> Dict[str, int]:
    """Quick stats for dashboard KPIs."""
    init_db()
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM violations WHERE status='ACTIVE'")
    active = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM violations WHERE status='RESOLVED'")
    resolved = cur.fetchone()[0]
    conn.close()
    return {"active": active, "resolved": resolved, "total": active + resolved}
