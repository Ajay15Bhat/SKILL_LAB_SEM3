"""
ClauseTrace Contract Version Operations, Analysis, and Approvals API Endpoints.
"""

from __future__ import annotations

import io
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.approval import Approval
from app.models.auth import User
from app.models.base import (
    ApprovalDecision,
    AuditAction,
    FindingStatus,
    ReviewStatus,
    UserRole,
    VersionStatus,
)
from app.models.contract import Clause, Contract, ContractVersion
from app.models.requirement import Finding, Requirement
from app.schemas import (
    AnalysisCreateResponse,
    ApprovalCreate,
    ApprovalRead,
    ClauseRead,
    FindingRead,
    VersionDetail,
    VersionRead,
)
from app.services.approval_service import approval_service
from app.services.audit_service import audit_service
from app.services.evaluator import evaluator
from app.services.storage import storage_service

router = APIRouter(prefix="/versions", tags=["Version Analyses & Approvals"])


@router.get("/{version_id}", response_model=VersionDetail)
async def get_version_detail(
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves contract version with its clauses and parent contract metadata."""
    stmt = (
        select(ContractVersion)
        .options(
            selectinload(ContractVersion.contract),
            selectinload(ContractVersion.clauses),
        )
        .where(
            ContractVersion.id == version_id,
            ContractVersion.organization_id == current_user.organization_id,
        )
    )
    res = await db.execute(stmt)
    version = res.scalars().first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract version not found in your organization.",
        )

    v_detail = VersionDetail.model_validate(version)
    if version.contract:
        v_detail.contract_title = version.contract.title
        v_detail.vendor_name = version.contract.vendor_name
    v_detail.clauses = [ClauseRead.model_validate(c) for c in version.clauses]
    return v_detail


@router.get("/{version_id}/clauses", response_model=List[ClauseRead])
async def list_version_clauses(
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists extracted clauses with page locations and offsets for a version."""
    # Verify version ownership
    v_check = await db.execute(
        select(ContractVersion.id).where(
            ContractVersion.id == version_id,
            ContractVersion.organization_id == current_user.organization_id,
        )
    )
    if not v_check.scalar():
        raise HTTPException(status_code=404, detail="Version not found.")

    stmt = (
        select(Clause)
        .where(Clause.contract_version_id == version_id)
        .order_by(Clause.clause_index.asc())
    )
    res = await db.execute(stmt)
    return [ClauseRead.model_validate(c) for c in res.scalars().all()]


@router.get("/{version_id}/download")
async def download_contract_file(
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Securely downloads the raw contract document binary."""
    stmt = select(ContractVersion).where(
        ContractVersion.id == version_id,
        ContractVersion.organization_id == current_user.organization_id,
    )
    res = await db.execute(stmt)
    version = res.scalars().first()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found.")

    file_bytes = storage_service.get_file_bytes(version.file_path)
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=version.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{version.file_name}"'},
    )


@router.post("/{version_id}/analyses", response_model=AnalysisCreateResponse)
async def run_version_analysis(
    version_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates organizational compliance requirements against this specific contract version.
    Produces evidence-backed findings linked to exact clauses.
    Findings are strictly tied to this version ID (no silent inheritance).
    """
    stmt = select(ContractVersion).where(
        ContractVersion.id == version_id,
        ContractVersion.organization_id == current_user.organization_id,
    )
    res = await db.execute(stmt)
    version = res.scalars().first()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found.")

    # Fetch requirements applicable to this organization and contract
    r_stmt = select(Requirement).where(
        Requirement.organization_id == current_user.organization_id,
        (Requirement.contract_id == None) | (Requirement.contract_id == version.contract_id),
    )
    r_res = await db.execute(r_stmt)
    requirements = r_res.scalars().all()

    if not requirements:
        return AnalysisCreateResponse(
            analysis_run_id=uuid.uuid4(),
            contract_version_id=version_id,
            total_requirements_evaluated=0,
            findings=[],
        )

    run_id = uuid.uuid4()
    created_findings: List[Finding] = []

    for req in requirements:
        # Check if finding already exists for this (req, version)
        f_exist = await db.execute(
            select(Finding).where(
                Finding.requirement_id == req.id,
                Finding.contract_version_id == version_id,
            )
        )
        existing = f_exist.scalars().first()

        if existing:
            # Re-evaluate
            new_f = await evaluator.evaluate_requirement(
                db=db,
                requirement=req,
                contract_version_id=version.id,
                organization_id=current_user.organization_id,
            )
            existing.status = new_f.status
            existing.evidence_clause_id = new_f.evidence_clause_id
            existing.evidence_quote = new_f.evidence_quote
            existing.confidence_score = new_f.confidence_score
            existing.analysis_notes = new_f.analysis_notes
            existing.suggested_by = new_f.suggested_by
            existing.review_status = ReviewStatus.PROPOSED
            created_findings.append(existing)
        else:
            finding = await evaluator.evaluate_requirement(
                db=db,
                requirement=req,
                contract_version_id=version.id,
                organization_id=current_user.organization_id,
            )
            db.add(finding)
            created_findings.append(finding)

    # Log audit event
    await audit_service.log_event(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.REQUIREMENT_EVALUATED,
        entity_type="CONTRACT_VERSION",
        entity_id=version.id,
        metadata_after={"total_evaluated": len(created_findings), "run_id": str(run_id)},
    )

    await db.commit()

    # Format findings with requirement metadata
    output_findings = []
    for f in created_findings:
        await db.refresh(f)
        f_read = FindingRead.model_validate(f)
        # Populate requirement details
        req_obj = next((r for r in requirements if r.id == f.requirement_id), None)
        if req_obj:
            f_read.requirement_title = req_obj.title
            f_read.requirement_category = req_obj.category

        if f.evidence_clause_id:
            c_res = await db.execute(select(Clause).where(Clause.id == f.evidence_clause_id))
            c = c_res.scalars().first()
            if c:
                f_read.evidence_page_number = c.page_number
                f_read.evidence_section_title = c.section_title
        output_findings.append(f_read)

    return AnalysisCreateResponse(
        analysis_run_id=run_id,
        contract_version_id=version_id,
        total_requirements_evaluated=len(output_findings),
        findings=output_findings,
    )


@router.post(
    "/{version_id}/approvals",
    response_model=ApprovalRead,
    status_code=status.HTTP_201_CREATED,
)
async def approve_contract_version(
    version_id: uuid.UUID,
    req: ApprovalCreate,
    current_user: User = Depends(require_roles(UserRole.REVIEWER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Formal sign-off on a specific contract version.
    Only Reviewers and Admins are authorized.
    Produces a cryptographic SHA-256 seal.
    Approving v1 never approves v2.
    """
    stmt = select(ContractVersion).where(
        ContractVersion.id == version_id,
        ContractVersion.organization_id == current_user.organization_id,
    )
    res = await db.execute(stmt)
    version = res.scalars().first()

    if not version:
        raise HTTPException(status_code=404, detail="Contract version not found.")

    approval = await approval_service.process_approval(
        db=db,
        version=version,
        approver=current_user,
        decision=req.decision,
        comments=req.comments,
    )

    audit_action = (
        AuditAction.APPROVAL_GRANTED
        if req.decision == ApprovalDecision.APPROVED
        else AuditAction.APPROVAL_REJECTED
    )
    await audit_service.log_event(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=audit_action,
        entity_type="CONTRACT_VERSION",
        entity_id=version.id,
        metadata_after={
            "decision": req.decision.value,
            "signature_hash": approval.signature_hash,
            "comments": req.comments,
        },
    )

    await db.commit()
    await db.refresh(approval)

    app_read = ApprovalRead.model_validate(approval)
    app_read.approver_name = current_user.full_name
    return app_read


@router.get("/{version_id}/approvals", response_model=List[ApprovalRead])
async def list_version_approvals(
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves approval history and cryptographic seals for a specific contract version."""
    stmt = (
        select(Approval)
        .options(selectinload(Approval.approver))
        .where(
            Approval.contract_version_id == version_id,
            Approval.organization_id == current_user.organization_id,
        )
        .order_by(Approval.created_at.desc())
    )
    res = await db.execute(stmt)
    approvals = res.scalars().all()

    output = []
    for a in approvals:
        a_read = ApprovalRead.model_validate(a)
        if a.approver:
            a_read.approver_name = a.approver.full_name
        output.append(a_read)
    return output
