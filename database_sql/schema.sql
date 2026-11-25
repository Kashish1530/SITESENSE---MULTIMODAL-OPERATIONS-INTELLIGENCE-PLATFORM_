-- =============================================================================
-- SITESENSE - MULTIMODAL OPERATIONS INTELLIGENCE PLATFORM
-- CORE DATA MODEL (PostgreSQL / Neon Database)
-- =============================================================================

-- Enable extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. SITES
-- The physical locations being inspected (stores, warehouses, construction sites, etc.)
CREATE TABLE IF NOT EXISTS sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100),
    location VARCHAR(255),
    active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. USERS
-- Role drives what the UI shows and the API allows (admin / manager / field / reviewer)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'manager', 'field', 'reviewer')),
    password_hash VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. INSPECTIONS
-- One upload session from one site
CREATE TABLE IF NOT EXISTS inspections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending' NOT NULL,
    job_id VARCHAR(255) UNIQUE
);

-- 4. MEDIA
-- Every uploaded file, with its storage path (image / video / doc)
CREATE TABLE IF NOT EXISTS media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (type IN ('image', 'video', 'doc')),
    path TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 5. DETECTIONS
-- One row per detected object; the evidence trail
CREATE TABLE IF NOT EXISTS detections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id UUID NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    class_name VARCHAR(100) NOT NULL,
    bbox JSONB NOT NULL, -- [x1, y1, x2, y2] absolute coordinates
    confidence NUMERIC(5, 4) NOT NULL,
    zone VARCHAR(100),
    frame_no INTEGER, -- for video frames; NULL for static images
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 6. EXTRACTIONS
-- Structured fields pulled from documents
CREATE TABLE IF NOT EXISTS extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id UUID NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    value TEXT,
    confidence NUMERIC(5, 4) NOT NULL,
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 7. POLICIES
-- The documents that rules are checked against
CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    version VARCHAR(50) DEFAULT '1.0' NOT NULL,
    source_file TEXT NOT NULL,
    effective_date DATE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 8. RULES
-- The machine-readable compliance rules
CREATE TABLE IF NOT EXISTS rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    rule_type VARCHAR(100) NOT NULL,
    parameters JSONB DEFAULT '{}'::jsonb,
    policy_ref VARCHAR(255),
    policy_id UUID REFERENCES policies(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 9. FINDINGS
-- The result of evaluating a rule - what the report is built from
CREATE TABLE IF NOT EXISTS findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL CHECK (status IN ('pass', 'fail', 'review')),
    evidence_ids JSONB DEFAULT '[]'::jsonb, -- array of detection IDs or media IDs
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 10. TICKETS
-- Actions raised from failures - agent proposes, human approves
CREATE TABLE IF NOT EXISTS tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'proposed' NOT NULL CHECK (status IN ('proposed', 'approved', 'rejected', 'in_progress', 'resolved', 'closed')),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMPTZ
);

-- 11. AGENT_RUNS
-- The audit trail for every agent interaction
CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    question TEXT NOT NULL,
    route VARCHAR(100),
    tools_called JSONB DEFAULT '[]'::jsonb,
    tokens INTEGER DEFAULT 0,
    cost NUMERIC(10, 6) DEFAULT 0.0,
    latency NUMERIC(10, 3), -- latency in seconds
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- PERFORMANCE INDEXES
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_inspections_site_id ON inspections(site_id);
CREATE INDEX IF NOT EXISTS idx_inspections_user_id ON inspections(user_id);
CREATE INDEX IF NOT EXISTS idx_inspections_status ON inspections(status);
CREATE INDEX IF NOT EXISTS idx_inspections_job_id ON inspections(job_id);

CREATE INDEX IF NOT EXISTS idx_media_inspection_id ON media(inspection_id);
CREATE INDEX IF NOT EXISTS idx_media_type ON media(type);

CREATE INDEX IF NOT EXISTS idx_detections_media_id ON detections(media_id);
CREATE INDEX IF NOT EXISTS idx_detections_class_name ON detections(class_name);
CREATE INDEX IF NOT EXISTS idx_detections_zone ON detections(zone);

CREATE INDEX IF NOT EXISTS idx_extractions_media_id ON extractions(media_id);
CREATE INDEX IF NOT EXISTS idx_extractions_reviewed_by ON extractions(reviewed_by);

CREATE INDEX IF NOT EXISTS idx_rules_policy_id ON rules(policy_id);
CREATE INDEX IF NOT EXISTS idx_rules_rule_type ON rules(rule_type);

CREATE INDEX IF NOT EXISTS idx_findings_inspection_id ON findings(inspection_id);
CREATE INDEX IF NOT EXISTS idx_findings_rule_id ON findings(rule_id);
CREATE INDEX IF NOT EXISTS idx_findings_status ON findings(status);

CREATE INDEX IF NOT EXISTS idx_tickets_finding_id ON tickets(finding_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);

CREATE INDEX IF NOT EXISTS idx_agent_runs_user_id ON agent_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_route ON agent_runs(route);

