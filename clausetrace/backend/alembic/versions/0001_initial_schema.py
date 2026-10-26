"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-26 19:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enums
    user_role = postgresql.ENUM('ADMIN', 'ANALYST', 'REVIEWER', 'AUDITOR', name='user_role', create_type=False)
    version_status = postgresql.ENUM('DRAFT', 'IN_REVIEW', 'APPROVED', 'REJECTED', name='version_status', create_type=False)
    job_status = postgresql.ENUM('QUEUED', 'PROCESSING', 'SUCCEEDED', 'FAILED', 'CANCELLED', name='job_status', create_type=False)
    job_type = postgresql.ENUM('EXTRACT_DOCUMENT', 'GENERATE_DIFF', 'EVALUATE_REQUIREMENTS', 'REINDEX_SEARCH', name='job_type', create_type=False)
    finding_status = postgresql.ENUM('SATISFIED', 'PARTIALLY_SATISFIED', 'NOT_SATISFIED', 'NOT_FOUND', 'NEEDS_REVIEW', name='finding_status', create_type=False)
    review_status = postgresql.ENUM('PROPOSED', 'CONFIRMED', 'OVERRIDDEN', name='review_status', create_type=False)
    approval_decision = postgresql.ENUM('APPROVED', 'REJECTED', name='approval_decision', create_type=False)
    obligation_status = postgresql.ENUM('PENDING', 'IN_PROGRESS', 'COMPLETED', 'OVERDUE', name='obligation_status', create_type=False)
    obligation_party = postgresql.ENUM('CUSTOMER', 'VENDOR', 'MUTUAL', name='obligation_party', create_type=False)
    obligation_frequency = postgresql.ENUM('ONE_TIME', 'WEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUAL', name='obligation_frequency', create_type=False)
    audit_action = postgresql.ENUM(
        'DOCUMENT_UPLOADED', 'VERSION_CREATED', 'VERSION_STATUS_CHANGED',
        'REQUIREMENT_CREATED', 'REQUIREMENT_UPDATED', 'REQUIREMENT_EVALUATED',
        'FINDING_CONFIRMED', 'FINDING_OVERRIDDEN', 'APPROVAL_GRANTED',
        'APPROVAL_REJECTED', 'OBLIGATION_CREATED', 'OBLIGATION_STATUS_CHANGED',
        'DIFF_GENERATED', name='audit_action', create_type=False
    )

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE user_role AS ENUM ('ADMIN', 'ANALYST', 'REVIEWER', 'AUDITOR');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
        DO $$ BEGIN
            CREATE TYPE version_status AS ENUM ('DRAFT', 'IN_REVIEW', 'APPROVED', 'REJECTED');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
        DO $$ BEGIN
            CREATE TYPE job_status AS ENUM ('QUEUED', 'PROCESSING', 'SUCCEEDED', 'FAILED', 'CANCELLED');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
        DO $$ BEGIN
            CREATE TYPE job_type AS ENUM ('EXTRACT_DOCUMENT', 'GENERATE_DIFF', 'EVALUATE_REQUIREMENTS', 'REINDEX_SEARCH');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
        DO $$ BEGIN
            CREATE TYPE finding_status AS ENUM ('SATISFIED', 'PARTIALLY_SATISFIED', 'NOT_SATISFIED', 'NOT_FOUND', 'NEEDS_REVIEW');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
        DO $$ BEGIN
            CREATE TYPE review_status AS ENUM ('PROPOSED', 'CONFIRMED', 'OVERRIDDEN');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
        DO $$ BEGIN
            CREATE TYPE approval_decision AS ENUM ('APPROVED', 'REJECTED');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
        DO $$ BEGIN
            CREATE TYPE obligation_status AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'OVERDUE');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
        DO $$ BEGIN
            CREATE TYPE obligation_party AS ENUM ('CUSTOMER', 'VENDOR', 'MUTUAL');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
        DO $$ BEGIN
            CREATE TYPE obligation_frequency AS ENUM ('ONE_TIME', 'WEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUAL');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
        DO $$ BEGIN
            CREATE TYPE audit_action AS ENUM (
                'DOCUMENT_UPLOADED', 'VERSION_CREATED', 'VERSION_STATUS_CHANGED',
                'REQUIREMENT_CREATED', 'REQUIREMENT_UPDATED', 'REQUIREMENT_EVALUATED',
                'FINDING_CONFIRMED', 'FINDING_OVERRIDDEN', 'APPROVAL_GRANTED',
                'APPROVAL_REJECTED', 'OBLIGATION_CREATED', 'OBLIGATION_STATUS_CHANGED',
                'DIFF_GENERATED'
            );
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)

    # Organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_organizations')),
        sa.UniqueConstraint('slug', name=op.f('uq_organizations_slug'))
    )
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True)

    # Users
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', user_role, nullable=False, server_default='ANALYST'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_users_organization_id_organizations'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_index('ix_users_org_role', 'users', ['organization_id', 'role'], unique=False)
    op.create_index(op.f('ix_users_organization_id'), 'users', ['organization_id'], unique=False)

    # Contracts
    op.create_table(
        'contracts',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('vendor_name', sa.String(length=255), nullable=False),
        sa.Column('contract_type', sa.String(length=100), server_default='MSA', nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_contracts_created_by_users'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_contracts_organization_id_organizations'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_contracts'))
    )
    op.create_index('ix_contracts_org_vendor', 'contracts', ['organization_id', 'vendor_name'], unique=False)
    op.create_index(op.f('ix_contracts_organization_id'), 'contracts', ['organization_id'], unique=False)

    # Contract Versions
    op.create_table(
        'contract_versions',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('contract_id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('sha256_checksum', sa.String(length=64), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('approval_status', version_status, server_default='DRAFT', nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], name=op.f('fk_contract_versions_contract_id_contracts'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_contract_versions_created_by_users'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_contract_versions_organization_id_organizations'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_contract_versions')),
        sa.UniqueConstraint('contract_id', 'sha256_checksum', name='uq_contract_sha256'),
        sa.UniqueConstraint('contract_id', 'version_number', name='uq_contract_version_number')
    )
    op.create_index('ix_contract_versions_org_status', 'contract_versions', ['organization_id', 'approval_status'], unique=False)
    op.create_index(op.f('ix_contract_versions_contract_id'), 'contract_versions', ['contract_id'], unique=False)
    op.create_index(op.f('ix_contract_versions_sha256_checksum'), 'contract_versions', ['sha256_checksum'], unique=False)

    # Clauses
    op.create_table(
        'clauses',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('contract_version_id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('clause_index', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('section_title', sa.String(length=255), nullable=True),
        sa.Column('text_content', sa.Text(), nullable=False),
        sa.Column('char_start', sa.Integer(), server_default='0', nullable=False),
        sa.Column('char_end', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['contract_version_id'], ['contract_versions.id'], name=op.f('fk_clauses_contract_version_id_contract_versions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_clauses_organization_id_organizations'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_clauses')),
        sa.UniqueConstraint('contract_version_id', 'clause_index', name='uq_version_clause_index')
    )
    # Add generated TSVector column and GIN index
    op.execute("""
        ALTER TABLE clauses ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english', coalesce(section_title, '') || ' ' || text_content)
        ) STORED;
    """)
    op.create_index('ix_clauses_search_vector', 'clauses', ['search_vector'], postgresql_using='gin')
    op.create_index('ix_clauses_version_page', 'clauses', ['contract_version_id', 'page_number'])

    # Requirements
    op.create_table(
        'requirements',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('contract_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), server_default='General', nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('search_keywords', sa.ARRAY(sa.String()), server_default='{}', nullable=False),
        sa.Column('is_mandatory', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], name=op.f('fk_requirements_contract_id_contracts'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_requirements_created_by_users'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_requirements_organization_id_organizations'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_requirements'))
    )
    op.create_index('ix_requirements_org_cat', 'requirements', ['organization_id', 'category'], unique=False)

    # Findings
    op.create_table(
        'findings',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('requirement_id', sa.UUID(), nullable=False),
        sa.Column('contract_version_id', sa.UUID(), nullable=False),
        sa.Column('status', finding_status, server_default='NEEDS_REVIEW', nullable=False),
        sa.Column('evidence_clause_id', sa.UUID(), nullable=True),
        sa.Column('evidence_quote', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('analysis_notes', sa.Text(), nullable=True),
        sa.Column('suggested_by', sa.String(length=50), server_default='DETERMINISTIC_SEARCH', nullable=False),
        sa.Column('review_status', review_status, server_default='PROPOSED', nullable=False),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['contract_version_id'], ['contract_versions.id'], name=op.f('fk_findings_contract_version_id_contract_versions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_clause_id'], ['clauses.id'], name=op.f('fk_findings_evidence_clause_id_clauses'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_findings_organization_id_organizations'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], name=op.f('fk_findings_requirement_id_requirements'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], name=op.f('fk_findings_reviewed_by_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_findings')),
        sa.UniqueConstraint('requirement_id', 'contract_version_id', name='uq_requirement_version_finding')
    )
    op.create_index('ix_findings_version_status', 'findings', ['contract_version_id', 'status'], unique=False)

    # Version Diffs
    op.create_table(
        'version_diffs',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('source_version_id', sa.UUID(), nullable=False),
        sa.Column('target_version_id', sa.UUID(), nullable=False),
        sa.Column('diff_summary', sa.Text(), nullable=False),
        sa.Column('diff_payload', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_version_diffs_organization_id_organizations'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_version_id'], ['contract_versions.id'], name=op.f('fk_version_diffs_source_version_id_contract_versions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_version_id'], ['contract_versions.id'], name=op.f('fk_version_diffs_target_version_id_contract_versions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_version_diffs')),
        sa.UniqueConstraint('source_version_id', 'target_version_id', name='uq_version_diff_pair')
    )
    op.create_index('ix_version_diffs_target', 'version_diffs', ['target_version_id'], unique=False)

    # Approvals
    op.create_table(
        'approvals',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('contract_version_id', sa.UUID(), nullable=False),
        sa.Column('approver_id', sa.UUID(), nullable=False),
        sa.Column('decision', approval_decision, server_default='APPROVED', nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('signature_hash', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id'], name=op.f('fk_approvals_approver_id_users'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['contract_version_id'], ['contract_versions.id'], name=op.f('fk_approvals_contract_version_id_contract_versions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_approvals_organization_id_organizations'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_approvals'))
    )
    op.create_index('ix_approvals_version_decision', 'approvals', ['contract_version_id', 'decision'], unique=False)

    # Obligations
    op.create_table(
        'obligations',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('contract_version_id', sa.UUID(), nullable=False),
        sa.Column('clause_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('party', obligation_party, server_default='VENDOR', nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('frequency', obligation_frequency, server_default='ONE_TIME', nullable=False),
        sa.Column('status', obligation_status, server_default='PENDING', nullable=False),
        sa.Column('assigned_to', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], name=op.f('fk_obligations_assigned_to_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['clause_id'], ['clauses.id'], name=op.f('fk_obligations_clause_id_clauses'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['contract_version_id'], ['contract_versions.id'], name=op.f('fk_obligations_contract_version_id_contract_versions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_obligations_organization_id_organizations'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_obligations'))
    )
    op.create_index('ix_obligations_org_due', 'obligations', ['organization_id', 'due_date'], unique=False)
    op.create_index('ix_obligations_version_status', 'obligations', ['contract_version_id', 'status'], unique=False)

    # Background Jobs (Native PostgreSQL Queue)
    op.create_table(
        'background_jobs',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('job_type', job_type, nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('status', job_status, server_default='QUEUED', nullable=False),
        sa.Column('priority', sa.Integer(), server_default='0', nullable=False),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_retries', sa.Integer(), server_default='3', nullable=False),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('locked_by', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_background_jobs'))
    )
    # Partial index for worker claiming:
    op.create_index(
        'ix_background_jobs_claim',
        'background_jobs',
        ['status', sa.text('priority DESC'), 'created_at'],
        postgresql_where=sa.text("status = 'QUEUED'"),
    )

    # Audit Logs (Append-only)
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('metadata_before', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata_after', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_audit_logs_organization_id_organizations'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_audit_logs_user_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    op.create_index('ix_audit_org_action_time', 'audit_logs', ['organization_id', 'action', 'created_at'], unique=False)
    op.create_index('ix_audit_entity', 'audit_logs', ['entity_type', 'entity_id'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('background_jobs')
    op.drop_table('obligations')
    op.drop_table('approvals')
    op.drop_table('version_diffs')
    op.drop_table('findings')
    op.drop_table('requirements')
    op.drop_table('clauses')
    op.drop_table('contract_versions')
    op.drop_table('contracts')
    op.drop_table('users')
    op.drop_table('organizations')

