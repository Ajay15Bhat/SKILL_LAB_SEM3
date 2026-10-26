-- ============================================================================
-- CLAUSETRACE: SWEET-SPOT DATABASE SCHEMA (6 PURPOSEFUL TABLES)
-- Clean, defensible, and 100% auditable for lab & project evaluations.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Users (Analyst vs Reviewer)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'ANALYST' CHECK (role IN ('ANALYST', 'REVIEWER')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Contracts (Agreement Container)
CREATE TABLE IF NOT EXISTS contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    vendor_name VARCHAR(255) NOT NULL,
    contract_type VARCHAR(100) NOT NULL DEFAULT 'MSA',
    description TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Contract Versions (Immutable with SHA-256 & Approval State)
CREATE TABLE IF NOT EXISTS contract_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    sha256_checksum VARCHAR(64) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    approval_status VARCHAR(50) NOT NULL DEFAULT 'DRAFT' CHECK (approval_status IN ('DRAFT', 'IN_REVIEW', 'APPROVED', 'REJECTED')),
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_contract_version UNIQUE (contract_id, version_number),
    CONSTRAINT uq_contract_sha256 UNIQUE (contract_id, sha256_checksum)
);

-- 4. Extracted Clauses (With PostgreSQL Full-Text Search tsvector & GIN index)
CREATE TABLE IF NOT EXISTS clauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_version_id UUID NOT NULL REFERENCES contract_versions(id) ON DELETE CASCADE,
    clause_index INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    section_title VARCHAR(255),
    text_content TEXT NOT NULL,
    char_start INTEGER NOT NULL DEFAULT 0,
    char_end INTEGER NOT NULL DEFAULT 0,
    search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(section_title, '') || ' ' || text_content)
    ) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_version_clause_index UNIQUE (contract_version_id, clause_index)
);
CREATE INDEX IF NOT EXISTS ix_clauses_fts ON clauses USING GIN(search_vector);

-- 5. Requirements (Compliance Policies / Rules)
CREATE TABLE IF NOT EXISTS requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL DEFAULT 'General',
    description TEXT NOT NULL,
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    is_mandatory BOOLEAN NOT NULL DEFAULT true,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. Findings (Evaluations - Version Tied: NO SILENT INHERITANCE)
CREATE TABLE IF NOT EXISTS findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id UUID NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    contract_version_id UUID NOT NULL REFERENCES contract_versions(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'NEEDS_REVIEW' CHECK (status IN ('SATISFIED', 'PARTIALLY_SATISFIED', 'NOT_SATISFIED', 'NOT_FOUND', 'NEEDS_REVIEW')),
    evidence_clause_id UUID REFERENCES clauses(id) ON DELETE SET NULL,
    evidence_quote TEXT,
    confidence_score DOUBLE PRECISION,
    analysis_notes TEXT,
    review_status VARCHAR(50) NOT NULL DEFAULT 'PROPOSED' CHECK (review_status IN ('PROPOSED', 'CONFIRMED', 'OVERRIDDEN')),
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_req_ver_finding UNIQUE (requirement_id, contract_version_id)
);

-- 7. Audit Logs (Append-Only Event Ledger for the Audit Timeline)
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Immutability Guardrail on Audit Log (Throws exception on UPDATE or DELETE)
CREATE OR REPLACE FUNCTION fn_audit_immutable()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit logs are immutable. UPDATE and DELETE operations are forbidden.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_immutable ON audit_logs;
CREATE TRIGGER trg_audit_immutable
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION fn_audit_immutable();

-- Insert Seed Demo Users
INSERT INTO users (id, email, full_name, role)
VALUES 
    ('00000000-0000-0000-0000-000000000001', 'analyst@clausetrace.io', 'Alex Analyst', 'ANALYST'),
    ('00000000-0000-0000-0000-000000000002', 'reviewer@clausetrace.io', 'Rachel Reviewer', 'REVIEWER')
ON CONFLICT (email) DO NOTHING;

-- Insert Seed Demo Users
INSERT INTO users (id, email, full_name, role)
VALUES 
    ('00000000-0000-0000-0000-000000000001', 'analyst@clausetrace.io', 'Alex Analyst', 'ANALYST'),
    ('00000000-0000-0000-0000-000000000002', 'reviewer@clausetrace.io', 'Rachel Reviewer', 'REVIEWER')
ON CONFLICT (email) DO NOTHING;

