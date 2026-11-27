"""
SITESENSE - Database Schema Update Migration Script
Updates the PostgreSQL/Neon Database schema for:
  - users
  - sites
  - inspections
as per user specification.
"""

import sys
import psycopg2
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from agentic.tools.query_database import get_db_url


def run_migration():
    db_url = get_db_url()
    print("Connecting to Neon PostgreSQL...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    # -------------------------------------------------------------------------
    # 1. USERS TABLE
    # Columns requested:
    # serial_no., user_id , first_name, last_name, supervision, site_id,
    # gender, phone_number, Is_valid, address[city, state, country, Pincode],
    # email , hashed_password, role, is_active, created_at, updated_at, last_login at
    # -------------------------------------------------------------------------
    print("Migrating 'users' table...")
    cur.execute("""
        -- Sequence for serial_no
        CREATE SEQUENCE IF NOT EXISTS users_serial_no_seq;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS serial_no INTEGER DEFAULT nextval('users_serial_no_seq');
        
        -- user_id (UUID)
        ALTER TABLE users ADD COLUMN IF NOT EXISTS user_id UUID;
        UPDATE users SET user_id = id WHERE user_id IS NULL;

        -- first_name, last_name
        ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(100);
        ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);
        UPDATE users SET 
            first_name = COALESCE(SPLIT_PART(name, ' ', 1), 'User'),
            last_name = COALESCE(NULLIF(SUBSTRING(name FROM POSITION(' ' IN name) + 1), ''), 'SiteSense')
        WHERE first_name IS NULL;

        -- supervision
        ALTER TABLE users ADD COLUMN IF NOT EXISTS supervision VARCHAR(255) DEFAULT 'Direct Site Manager';

        -- site_id (foreign key to sites)
        ALTER TABLE users ADD COLUMN IF NOT EXISTS site_id UUID REFERENCES sites(id) ON DELETE SET NULL;

        -- gender
        ALTER TABLE users ADD COLUMN IF NOT EXISTS gender VARCHAR(20) DEFAULT 'Unspecified';

        -- phone_number
        ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(50) DEFAULT '+1-555-0199';

        -- is_valid (Is_valid)
        ALTER TABLE users ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE;

        -- address (JSONB structure + individual fields)
        ALTER TABLE users ADD COLUMN IF NOT EXISTS address JSONB DEFAULT '{"city": "London", "state": "Greater London", "country": "United Kingdom", "pincode": "EC1A 1BB"}'::jsonb;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS city VARCHAR(100) DEFAULT 'London';
        ALTER TABLE users ADD COLUMN IF NOT EXISTS state VARCHAR(100) DEFAULT 'Greater London';
        ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(100) DEFAULT 'United Kingdom';
        ALTER TABLE users ADD COLUMN IF NOT EXISTS pincode VARCHAR(20) DEFAULT 'EC1A 1BB';

        -- hashed_password (mirrors password_hash)
        ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255);
        UPDATE users SET hashed_password = password_hash WHERE hashed_password IS NULL;

        -- last_login_at (last_login at)
        ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;
    """)
    print("  -> 'users' table migration complete.")

    # -------------------------------------------------------------------------
    # 2. SITES TABLE
    # Columns requested:
    # serial_no., site_id, user_id, name, type, city, state, country, Pincode,
    # is_active, created_at, updated_at
    # -------------------------------------------------------------------------
    print("Migrating 'sites' table...")
    cur.execute("""
        -- Sequence for serial_no
        CREATE SEQUENCE IF NOT EXISTS sites_serial_no_seq;
        ALTER TABLE sites ADD COLUMN IF NOT EXISTS serial_no INTEGER DEFAULT nextval('sites_serial_no_seq');

        -- site_id (UUID)
        ALTER TABLE sites ADD COLUMN IF NOT EXISTS site_id UUID;
        UPDATE sites SET site_id = id WHERE site_id IS NULL;

        -- user_id (site lead / manager)
        ALTER TABLE sites ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL;

        -- city, state, country, pincode
        ALTER TABLE sites ADD COLUMN IF NOT EXISTS city VARCHAR(100) DEFAULT 'London';
        ALTER TABLE sites ADD COLUMN IF NOT EXISTS state VARCHAR(100) DEFAULT 'Greater London';
        ALTER TABLE sites ADD COLUMN IF NOT EXISTS country VARCHAR(100) DEFAULT 'United Kingdom';
        ALTER TABLE sites ADD COLUMN IF NOT EXISTS pincode VARCHAR(20) DEFAULT 'E1 6AN';

        -- is_active
        ALTER TABLE sites ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
        UPDATE sites SET is_active = COALESCE(active, TRUE) WHERE is_active IS NULL;
    """)
    print("  -> 'sites' table migration complete.")

    # -------------------------------------------------------------------------
    # 3. INSPECTIONS TABLE
    # Columns requested:
    # serial_no., inspection_id, site_id, user_id, status, job_id, pass_rate,
    # summary, comments, created_at, updated_at
    # -------------------------------------------------------------------------
    print("Migrating 'inspections' table...")
    cur.execute("""
        -- Sequence for serial_no
        CREATE SEQUENCE IF NOT EXISTS inspections_serial_no_seq;
        ALTER TABLE inspections ADD COLUMN IF NOT EXISTS serial_no INTEGER DEFAULT nextval('inspections_serial_no_seq');

        -- inspection_id (UUID)
        ALTER TABLE inspections ADD COLUMN IF NOT EXISTS inspection_id UUID;
        UPDATE inspections SET inspection_id = id WHERE inspection_id IS NULL;

        -- comments
        ALTER TABLE inspections ADD COLUMN IF NOT EXISTS comments TEXT DEFAULT 'Routine compliance verification audit.';

        -- updated_at
        ALTER TABLE inspections ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;
    """)
    print("  -> 'inspections' table migration complete.")

    # Populate serial_no for existing rows that might have NULL
    cur.execute("""
        DO $$
        DECLARE
            r RECORD;
            i INTEGER := 1;
        BEGIN
            FOR r IN SELECT id FROM users WHERE serial_no IS NULL ORDER BY created_at LOOP
                UPDATE users SET serial_no = i WHERE id = r.id;
                i := i + 1;
            END LOOP;

            i := 1;
            FOR r IN SELECT id FROM sites WHERE serial_no IS NULL ORDER BY created_at LOOP
                UPDATE sites SET serial_no = i WHERE id = r.id;
                i := i + 1;
            END LOOP;

            i := 1;
            FOR r IN SELECT id FROM inspections WHERE serial_no IS NULL ORDER BY created_at LOOP
                UPDATE inspections SET serial_no = i WHERE id = r.id;
                i := i + 1;
            END LOOP;
        END $$;
    """)

    # Sync sequences
    cur.execute("""
        SELECT setval('users_serial_no_seq', COALESCE((SELECT MAX(serial_no) FROM users), 0) + 1, false);
        SELECT setval('sites_serial_no_seq', COALESCE((SELECT MAX(serial_no) FROM sites), 0) + 1, false);
        SELECT setval('inspections_serial_no_seq', COALESCE((SELECT MAX(serial_no) FROM inspections), 0) + 1, false);
    """)

    # Verification query
    print("\n--- SCHEMA VERIFICATION ---")
    for tbl in ["users", "sites", "inspections"]:
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """, (tbl,))
        cols = cur.fetchall()
        print(f"\nTABLE: {tbl.upper()} ({len(cols)} columns)")
        for c in cols:
            print(f"  - {c[0]}: {c[1]} (nullable: {c[2]})")

    conn.close()
    print("\nMigration completed successfully!")


if __name__ == "__main__":
    run_migration()
