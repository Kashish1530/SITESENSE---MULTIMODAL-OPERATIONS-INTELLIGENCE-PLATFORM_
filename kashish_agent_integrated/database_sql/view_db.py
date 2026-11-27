"""
SITESENSE - Database Inspector for Neon PostgreSQL
Displays tables, row counts, and sample records directly from Neon DB.
"""

import os
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

def load_env(env_path: Path):
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

current_dir = Path(__file__).resolve().parent
load_env(current_dir / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

TABLES = [
    "sites",
    "users",
    "inspections",
    "media",
    "detections",
    "extractions",
    "policies",
    "rules",
    "findings",
    "tickets",
    "agent_runs",
]

def inspect_database():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("================================================================================")
    print("                 LIVE DATA IN NEON DATABASE (neondb)                            ")
    print("================================================================================")

    for table in TABLES:
        # Get count
        cur.execute(f"SELECT COUNT(*) AS total FROM {table};")
        total = cur.fetchone()["total"]

        print(f"\nTABLE: {table.upper()} (Total Rows: {total})")
        print("-" * 80)

        # Fetch sample rows
        cur.execute(f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT 3;")
        rows = cur.fetchall()

        if not rows:
            print("  (Empty table)")
            continue

        for i, row in enumerate(rows, 1):
            formatted_fields = []
            for k, v in row.items():
                v_str = str(v)
                if len(v_str) > 60:
                    v_str = v_str[:57] + "..."
                formatted_fields.append(f"{k}: {v_str}")
            print(f"  [{i}] " + " | ".join(formatted_fields))

    cur.close()
    conn.close()
    print("\n================================================================================")

if __name__ == "__main__":
    inspect_database()

