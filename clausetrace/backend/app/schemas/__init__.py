"""
ClauseTrace Core Pydantic Schemas.
Request & Response models with full type validation and OpenAPI documentation.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import (
    ApprovalDecision,
    AuditAction,
    FindingStatus,
    JobStatus,
    JobType,
    ObligationFrequency,
    ObligationParty,
    ObligationStatus,
    ReviewStatus,
    UserRole,
    VersionStatus,
)


# ============================================================================
# AUTH & ORG SCHEMAS
# ============================================================================

class OrganizationRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str


class LoginResponse(BaseModel):
    user: UserRead
    token: str
    organization: OrganizationRead


# ============================================================================
# CONTRACT & VERSION SCHEMAS
# ============================================================================

class ContractCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    vendor_name: str = Field(..., min_length=2, max_length=255)
    contract_type: str = Field(default="MSA", max_length=100)
    description: Optional[str] = None


class ContractRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    vendor_name: str
    contract_type: str
    description: Optional[str] = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    latest_version: Optional[int] = None
    latest_version_id: Optional[uuid.UUID] = None
    latest_status: Optional[VersionStatus] = None

    model_config = ConfigDict(from_attributes=True)


class VersionRead(BaseModel):
    id: uuid.UUID
    contract_id: uuid.UUID
    organization_id: uuid.UUID
    version_number: int
    sha256_checksum: str
    file_name: str
    file_size_bytes: int
    mime_type: str
    approval_status: VersionStatus
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    created_by: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClauseRead(BaseModel):
    id: uuid.UUID
    contract_version_id: uuid.UUID
    clause_index: int
    page_number: int
    section_title: Optional[str] = None
    text_content: str
    char_start: int
    char_end: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContractDetail(ContractRead):
    versions: List[VersionRead] = []


class VersionDetail(VersionRead):
    contract_title: Optional[str] = None
    vendor_name: Optional[str] = None
    clauses: List[ClauseRead] = []


# ============================================================================
# REQUIREMENTS & FINDINGS SCHEMAS
# ============================================================================

class RequirementCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    category: str = Field(default="General", max_length=100)
    description: str = Field(..., min_length=5)
    search_keywords: List[str] = Field(default_factory=list)
    is_mandatory: bool = True
    contract_id: Optional[uuid.UUID] = None


class RequirementUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    search_keywords: Optional[List[str]] = None
    is_mandatory: Optional[bool] = None


class RequirementRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    contract_id: Optional[uuid.UUID] = None
    title: str
    category: str
    description: str
    search_keywords: List[str]
    is_mandatory: bool
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FindingRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    requirement_id: uuid.UUID
    contract_version_id: uuid.UUID
    status: FindingStatus
    evidence_clause_id: Optional[uuid.UUID] = None
    evidence_quote: Optional[str] = None
    confidence_score: Optional[float] = None
    analysis_notes: Optional[str] = None
    suggested_by: str
    review_status: ReviewStatus
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    requirement_title: Optional[str] = None
    requirement_category: Optional[str] = None
    evidence_page_number: Optional[int] = None
    evidence_section_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FindingDecisionUpdate(BaseModel):
    decision: ReviewStatus = Field(..., description="CONFIRMED or OVERRIDDEN")
    overridden_status: Optional[FindingStatus] = None
    override_reason: Optional[str] = None


class AnalysisCreateResponse(BaseModel):
    analysis_run_id: uuid.UUID
    contract_version_id: uuid.UUID
    total_requirements_evaluated: int
    findings: List[FindingRead]


# ============================================================================
# COMPARISON / DIFF SCHEMAS
# ============================================================================

class CompareRequest(BaseModel):
    source_version_id: uuid.UUID
    target_version_id: uuid.UUID


class ModifiedClauseDiff(BaseModel):
    clause_index: int
    page_number: int
    section_title: Optional[str] = None
    source_text: str
    target_text: str
    diff_type: str = "MODIFIED"  # ADDED, REMOVED, MODIFIED
    highlighted_changes: Optional[List[Dict[str, Any]]] = None


class VersionDiffRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    source_version_id: uuid.UUID
    target_version_id: uuid.UUID
    diff_summary: str
    diff_payload: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# APPROVAL SCHEMAS
# ============================================================================

class ApprovalCreate(BaseModel):
    decision: ApprovalDecision = Field(default=ApprovalDecision.APPROVED)
    comments: Optional[str] = None


class ApprovalRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    contract_version_id: uuid.UUID
    approver_id: uuid.UUID
    approver_name: Optional[str] = None
    decision: ApprovalDecision
    comments: Optional[str] = None
    signature_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# OBLIGATION SCHEMAS
# ============================================================================

class ObligationCreate(BaseModel):
    contract_version_id: uuid.UUID
    clause_id: Optional[uuid.UUID] = None
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    party: ObligationParty = ObligationParty.VENDOR
    due_date: Optional[date] = None
    frequency: ObligationFrequency = ObligationFrequency.ONE_TIME
    assigned_to: Optional[uuid.UUID] = None


class ObligationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    party: Optional[ObligationParty] = None
    due_date: Optional[date] = None
    frequency: Optional[ObligationFrequency] = None
    status: Optional[ObligationStatus] = None
    assigned_to: Optional[uuid.UUID] = None


class ObligationRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    contract_version_id: uuid.UUID
    clause_id: Optional[uuid.UUID] = None
    title: str
    description: str
    party: ObligationParty
    due_date: Optional[date] = None
    frequency: ObligationFrequency
    status: ObligationStatus
    assigned_to: Optional[uuid.UUID] = None
    assignee_name: Optional[str] = None
    is_overdue: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# JOB & AUDIT SCHEMAS
# ============================================================================

class JobRead(BaseModel):
    id: uuid.UUID
    job_type: JobType
    status: JobStatus
    priority: int
    retry_count: int
    max_retries: int
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    actor_email: Optional[str] = None
    action: AuditAction
    entity_type: str
    entity_id: uuid.UUID
    metadata_before: Optional[Dict[str, Any]] = None
    metadata_after: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
