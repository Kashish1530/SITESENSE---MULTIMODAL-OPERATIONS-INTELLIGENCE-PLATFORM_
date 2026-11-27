import os
import uuid
from datetime import datetime, timezone
import psycopg2
from dotenv import load_dotenv
import bcrypt

load_dotenv('backend/.env')
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')

# Delete stray test user kashish@gmail.com
cur.execute("DELETE FROM site_memberships WHERE user_id IN (SELECT id FROM users WHERE email='kashish@gmail.com')")
cur.execute("DELETE FROM users WHERE email='kashish@gmail.com'")

# Sites
warehouse_id = '3591c762-1cb9-4fd4-9be0-f15ca5514c64'
construction_id = '20692bfe-c271-4773-a310-81295a5a1b13'

# Clean warehouse users memberships: field1 and reviewer1 and manager should only belong to warehouse
cur.execute('SELECT id FROM users WHERE email=%s', ('field1@sitesense.io',))
field1_id = cur.fetchone()[0]
cur.execute('SELECT id FROM users WHERE email=%s', ('reviewer1@sitesense.io',))
reviewer1_id = cur.fetchone()[0]
cur.execute('SELECT id FROM users WHERE email=%s', ('manager@sitesense.io',))
manager1_id = cur.fetchone()[0]

# Remove from all site memberships first
cur.execute('DELETE FROM site_memberships WHERE user_id IN (%s, %s, %s)', (field1_id, reviewer1_id, manager1_id))

now = datetime.now(timezone.utc)

# Insert warehouse memberships
for uid in [field1_id, reviewer1_id, manager1_id]:
    cur.execute(
        'INSERT INTO site_memberships (id, user_id, site_id, created_at) VALUES (%s, %s, %s, %s)',
        (str(uuid.uuid4()), uid, warehouse_id, now)
    )

# 4 Construction Users
construction_users = [
    ('Skyline Construction Admin', 'admin.skyline@sitesense.io', 'admin'),
    ('Skyline Construction Manager', 'manager.skyline@sitesense.io', 'manager'),
    ('Skyline Safety Reviewer', 'reviewer.skyline@sitesense.io', 'reviewer'),
    ('Skyline Field Supervisor', 'field.skyline@sitesense.io', 'field')
]

pw_hash = hash_pw('SiteSense@2026')

for name, email, role in construction_users:
    cur.execute('SELECT id FROM users WHERE email=%s', (email,))
    row = cur.fetchone()
    if row:
        u_id = row[0]
        cur.execute(
            'UPDATE users SET name=%s, role=%s, password_hash=%s, is_active=true WHERE id=%s',
            (name, role, pw_hash, u_id)
        )
    else:
        u_id = str(uuid.uuid4())
        cur.execute(
            'INSERT INTO users (id, name, email, role, password_hash, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, true, %s, %s)',
            (u_id, name, email, role, pw_hash, now, now)
        )
    
    # Ensure site membership strictly to construction site
    cur.execute('DELETE FROM site_memberships WHERE user_id=%s', (u_id,))
    cur.execute(
        'INSERT INTO site_memberships (id, user_id, site_id, created_at) VALUES (%s, %s, %s, %s)',
        (str(uuid.uuid4()), u_id, construction_id, now)
    )

conn.commit()
print('Successfully configured warehouse and construction users in Neon PostgreSQL database!')

cur.execute('''
SELECT u.name, u.email, u.role, s.name, s.type 
FROM users u 
LEFT JOIN site_memberships sm ON u.id = sm.user_id 
LEFT JOIN sites s ON sm.site_id = s.id 
ORDER BY s.type NULLS FIRST, u.role
''')
for r in cur.fetchall():
    print(r)

conn.close()
