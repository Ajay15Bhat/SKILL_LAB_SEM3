-- ============================================================================
-- CLAUSETRACE: PHASE 1 DATABASE SMOKE TEST
-- Run this in the Supabase SQL Editor after executing init_schema_and_rls.sql
-- ============================================================================

-- 1. Insert a Test Tenant & User
DO $$
DECLARE
    v_org_id UUID;
    v_user_id UUID := '00000000-0000-0000-0000-000000000001'::UUID;
    v_contract_id UUID;
    v_version_id UUID;
    v_clause_id UUID;
    v_req_id UUID;
BEGIN
    -- Organization
    INSERT INTO public.organizations (name, slug)
    VALUES ('Acme Corp', 'acme-corp')
    ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
    RETURNING id INTO v_org_id;

    -- User Profile
    INSERT INTO public.users (id, organization_id, email, full_name, role)
    VALUES (v_user_id, v_org_id, 'analyst@acme.com', 'Alex Analyst', 'ANALYST')
    ON CONFLICT (id) DO NOTHING;

    -- Contract Container
    INSERT INTO public.contracts (organization_id, title, vendor_name, created_by)
    VALUES (v_org_id, 'Cloud Hosting Agreement', 'CloudProvider Inc', v_user_id)
    RETURNING id INTO v_contract_id;

    -- Contract Version 1 (Immutable)
    INSERT INTO public.contract_versions (
        contract_id, organization_id, version_number, sha256_checksum,
        file_name, file_path, file_size_bytes, mime_type, approval_status, created_by
    )
    VALUES (
        v_contract_id, v_org_id, 1, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'hosting_agreement_v1.pdf', 'storage/contracts/hosting_agreement_v1.pdf', 245000, 'application/pdf', 'DRAFT', v_user_id
    )
    RETURNING id INTO v_version_id;

    -- Extracted Clause with Full-Text Search Vector
    INSERT INTO public.clauses (
        contract_version_id, organization_id, clause_index, page_number,
        section_title, text_content
    )
    VALUES (
        v_version_id, v_org_id, 1, 1,
        'Section 14: Termination',
        'Either party may terminate this Agreement without cause upon giving at least thirty (30) days prior written notice to the other party.'
    )
    RETURNING id INTO v_clause_id;

    -- Requirement Rule
    INSERT INTO public.requirements (
        organization_id, title, category, description, search_keywords, is_mandatory, created_by
    )
    VALUES (
        v_org_id, '30-Day Termination Notice', 'Termination',
        'Vendor agreement must allow termination with at least 30 days prior written notice.',
        ARRAY['terminate', 'notice', 'days', 'written'], true, v_user_id
    )
    RETURNING id INTO v_req_id;

    -- Finding (Evidence-Grounded, strictly tied to v1)
    INSERT INTO public.findings (
        organization_id, requirement_id, contract_version_id, status,
        evidence_clause_id, evidence_quote, confidence_score, suggested_by, review_status
    )
    VALUES (
        v_org_id, v_req_id, v_version_id, 'SATISFIED',
        v_clause_id, 'Either party may terminate this Agreement without cause upon giving at least thirty (30) days prior written notice',
        0.98, 'DETERMINISTIC_SEARCH', 'PROPOSED'
    );

    -- Test Audit Log Entry
    INSERT INTO public.audit_logs (
        organization_id, user_id, action, entity_type, entity_id, metadata_after
    )
    VALUES (
        v_org_id, v_user_id, 'VERSION_CREATED', 'contract_version', v_version_id,
        '{"version_number": 1, "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}'::jsonb
    );

    RAISE NOTICE 'SMOKE TEST DATA INSERTED SUCCESSFULLY!';
END $$;

-- 2. Verify Deterministic Full-Text Search Retrieval (tsvector / ts_rank_cd)
SELECT 
    c.clause_index,
    c.section_title,
    c.page_number,
    c.text_content,
    ts_rank_cd(c.search_vector, plainto_tsquery('english', 'termination 30 days notice')) AS relevance_score
FROM public.clauses c
WHERE c.search_vector @@ plainto_tsquery('english', 'termination 30 days notice')
ORDER BY relevance_score DESC;

-- 3. Verify Guardrail: Audit Log Immutability
-- This command MUST fail with an exception:
-- UPDATE public.audit_logs SET action = 'TAMPERED';

