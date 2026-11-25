-- =============================================================================
-- SITESENSE - SITE TEXT INTELLIGENCE (OCR + Intelligence Database Schema)
-- Target: PostgreSQL / Neon Database
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- 1. Top-Level Record — One row per upload
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ocr_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id VARCHAR(255) NOT NULL DEFAULT 'SITE-DEFAULT',
    inspection_id VARCHAR(255) NULL,
    media_name VARCHAR(512) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    full_text TEXT NOT NULL DEFAULT '',
    translated_text TEXT NULL,
    is_translated BOOLEAN NOT NULL DEFAULT FALSE,
    processing_time_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0 CHECK (processing_time_ms >= 0),
    annotated_image_base64 TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_ocr_reports_site_id
    ON ocr_reports (site_id);
CREATE INDEX IF NOT EXISTS idx_ocr_reports_inspection_id
    ON ocr_reports (inspection_id);
CREATE INDEX IF NOT EXISTS idx_ocr_reports_timestamp
    ON ocr_reports (timestamp DESC);

-- -----------------------------------------------------------------------------
-- 2. Entity Table — One row per extracted entity
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ocr_entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES ocr_reports(report_id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL CHECK (
        entity_type IN (
            'equipment_id',
            'serial_number',
            'model_number',
            'pallet_tag',
            'sku_code',
            'rack_location',
            'quantity',
            'capacity_rating',
            'inspection_date',
            'expiry_date',
            'safety_signage',
            'certification',
            'barcode_data',
            'qr_data',
            'general_text'
        )
    ),
    raw_text TEXT NOT NULL,
    normalized_value TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    bounding_box JSONB NOT NULL DEFAULT '[]'::jsonb,
    verification_status VARCHAR(50) NOT NULL DEFAULT 'needs_review' CHECK (
        verification_status IN ('auto_approved', 'needs_review', 'rejected')
    ),
    review_reason TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_ocr_entities_report_id
    ON ocr_entities (report_id);
CREATE INDEX IF NOT EXISTS idx_ocr_entities_entity_type
    ON ocr_entities (entity_type);
CREATE INDEX IF NOT EXISTS idx_ocr_entities_verification_status
    ON ocr_entities (verification_status);

-- -----------------------------------------------------------------------------
-- 3. Review Queue Table — Entities requiring human validation
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ocr_review_queue (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES ocr_reports(report_id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL CHECK (
        entity_type IN (
            'equipment_id',
            'serial_number',
            'model_number',
            'pallet_tag',
            'sku_code',
            'rack_location',
            'quantity',
            'capacity_rating',
            'inspection_date',
            'expiry_date',
            'safety_signage',
            'certification',
            'barcode_data',
            'qr_data',
            'general_text'
        )
    ),
    raw_text TEXT NOT NULL,
    normalized_value TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    bounding_box JSONB NOT NULL DEFAULT '[]'::jsonb,
    verification_status VARCHAR(50) NOT NULL DEFAULT 'needs_review' CHECK (
        verification_status IN ('auto_approved', 'needs_review', 'rejected')
    ),
    review_reason TEXT NULL,
    review_status VARCHAR(50) NULL DEFAULT 'pending' CHECK (
        review_status IS NULL OR review_status IN ('pending', 'approved', 'rejected')
    )
);

CREATE INDEX IF NOT EXISTS idx_ocr_review_queue_report_id
    ON ocr_review_queue (report_id);
CREATE INDEX IF NOT EXISTS idx_ocr_review_queue_verification_status
    ON ocr_review_queue (verification_status);
CREATE INDEX IF NOT EXISTS idx_ocr_review_queue_review_status
    ON ocr_review_queue (review_status);

-- -----------------------------------------------------------------------------
-- 4. Compliance-Check Table — One row per rule evaluation
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ocr_compliance_checks (
    check_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES ocr_reports(report_id) ON DELETE CASCADE,
    rule_id VARCHAR(100) NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    policy_reference VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (
        status IN ('compliant', 'non_compliant', 'flagged', 'insufficient_data')
    ),
    details TEXT NOT NULL,
    evidence_text TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_ocr_compliance_checks_report_id
    ON ocr_compliance_checks (report_id);
CREATE INDEX IF NOT EXISTS idx_ocr_compliance_checks_rule_id
    ON ocr_compliance_checks (rule_id);
CREATE INDEX IF NOT EXISTS idx_ocr_compliance_checks_status
    ON ocr_compliance_checks (status);

-- -----------------------------------------------------------------------------
-- 5. Gen-AI Context Table — Optional LLM grounding context
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ocr_genai_contexts (
    context_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES ocr_reports(report_id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_ocr_genai_contexts_report_id
    ON ocr_genai_contexts (report_id);
