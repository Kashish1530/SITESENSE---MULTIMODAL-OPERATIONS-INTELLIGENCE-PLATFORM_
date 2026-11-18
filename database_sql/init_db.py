"""
SITESENSE - Database Initialization Script for Neon PostgreSQL
Reads schema.sql and creates all tables, foreign keys, and indexes in Neon DB.
"""

import os
import sys
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Load .env file manually if python-dotenv is not installed
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
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment or .env file.")
    sys.exit(1)

def init_neon_database():
    print(f"Connecting to Neon Database...")
    schema_file = current_dir / "schema.sql"
    if not schema_file.exists():
        print(f"ERROR: {schema_file} not found.")
        sys.exit(1)

    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        print("Executing schema.sql DDL statements...")
        cur.execute(schema_sql)
        print("Schema execution completed successfully!\n")

        # Verify created tables
        expected_tables = [
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

        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        all_tables = [row[0] for row in cur.fetchall()]

        print("==================================================")
        print("VERIFICATION OF TABLES IN NEON DATABASE:")
        print("==================================================")
        all_present = True
        for table in expected_tables:
            if table in all_tables:
                cur.execute(f"SELECT COUNT(*) FROM information_schema.columns WHERE table_name = '{table}';")
                col_count = cur.fetchone()[0]
                print(f" [OK] Table '{table}': {col_count} columns")
            else:
                print(f" [MISSING] Table '{table}' not found!")
                all_present = False

        print("==================================================")
        if all_present:
            print("SUCCESS: All 11 Core Data Model tables exist in Neon DB.")
        else:
            print("WARNING: Some tables could not be verified.")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Database error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_neon_database()

