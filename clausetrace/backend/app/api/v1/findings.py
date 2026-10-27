"""
ClauseTrace Evidence-Backed Findings and Human Review Decisions API Endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.auth import User
from app.models.base import AuditAction, FindingStatus, ReviewStatus, UserRole
from app.models.contract import Clause
from app.models.requirement import Finding, Requirement
from app.schemas import ClauseRead, FindingDecisionUpdate, FindingRead
from app.services.audit_service import audit_service

router = APIRouter(prefix="/findings", tags=["Findings & Human Review"])


@router.get("", response_model=List[FindingRead])
async def list_findings(
    contract_version_id: Optional[uuid.UUID] = None,
    requirement_id: Optional[uuid.UUID] = None,
    status_filter: Optional[FindingStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists findings with optional filtering by version, requirement, or compliance status."""
    stmt = (
        select(Finding)
        .options(
            selectinload(Finding.requirement),
            selectinload(Finding.evidence_clause),
        )
        .where(Finding.organization_id == current_user.organization_id)
        .order_by(Finding.created_at.desc())
    )
    if contract_version_id:
        stmt = stmt.where(Finding.contract_version_id == contract_version_id)
    if requirement_id:
        stmt = stmt.where(Finding.requirement_id == requirement_id)
    if status_filter:
        stmt = stmt.where(Finding.status == status_filter)

    res = await db.execute(stmt)
    findings = res.scalars().all()

    output = []
    for f in findings:
        f_read = FindingRead.model_validate(f)
        if f.requirement:
            f_read.requirement_title = f.requirement.title
            f_read.requirement_category = f.requirement.category
        if f.evidence_clause:
            f_read.evidence_page_number = f.evidence_clause.page_number
            f_read.evidence_section_title = f.evidence_clause.section_title
        output.append(f_read)
    return output


@router.get("/{finding_id}", response_model=FindingRead)
async def get_finding(
    finding_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves finding details and citations."""
    stmt = (
        select(Finding)
        .options(
            selectinload(Finding.requirement),
            selectinload(Finding.evidence_clause),
        )
        .where(
            Finding.id == finding_id,
            Finding.organization_id == current_user.organization_id,
        )
    )
    res = await db.execute(stmt)
    finding = res.scalars().first()

    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    f_read = FindingRead.model_validate(finding)
    if finding.requirement:
        f_read.requirement_title = finding.requirement.title
        f_read.requirement_category = finding.requirement.category
    if finding.evidence_clause:
        f_read.evidence_page_number = finding.evidence_clause.page_number
        f_read.evidence_section_title = finding.evidence_clause.section_title
    return f_read


@router.get("/{finding_id}/evidence", response_model=ClauseRead)
async def get_finding_evidence(
    finding_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves the full underlying contract clause that served as evidence."""
    stmt = (
        select(Clause)
        .join(Finding, Finding.evidence_clause_id == Clause.id)
        .where(
            Finding.id == finding_id,
            Finding.organization_id == current_user.organization_id,
        )
    )
    res = await db.execute(stmt)
    clause = res.scalars().first()

    if not clause:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No source clause evidence attached to this finding.",
        )
    return clause


@router.patch("/{finding_id}/decision", response_model=FindingRead)
async def record_reviewer_decision(
    finding_id: uuid.UUID,
    req: FindingDecisionUpdate,
    current_user: User = Depends(require_roles(UserRole.REVIEWER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Human reviewer confirms or overrides a machine-generated finding.
    Preserves audit trail of reviewer identity, decision, and justification.
    """
    stmt = (
        select(Finding)
        .options(
            selectinload(Finding.requirement),
            selectinload(Finding.evidence_clause),
        )
        .where(
            Finding.id == finding_id,
            Finding.organization_id == current_user.organization_id,
        )
    )
    res = await db.execute(stmt)
    finding = res.scalars().first()

    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    now = datetime.now(timezone.utc)
    before_status = str(finding.status.value if hasattr(finding.status, "value") else finding.status)
    before_review = str(finding.review_status.value if hasattr(finding.review_status, "value") else finding.review_status)

    if req.decision == ReviewStatus.CONFIRMED:
        finding.review_status = ReviewStatus.CONFIRMED
        finding.reviewed_by = current_user.id
        finding.reviewed_at = now
        action = AuditAction.FINDING_CONFIRMED
    elif req.decision == ReviewStatus.OVERRIDDEN:
        if not req.overridden_status:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Overridden findings must specify the new 'overridden_status'.",
            )
        finding.review_status = ReviewStatus.OVERRIDDEN
        finding.status = req.overridden_status
        finding.reviewed_by = current_user.id
        finding.reviewed_at = now
        if req.override_reason:
            finding.analysis_notes = (finding.analysis_notes or "") + f"\n[Reviewer Override by {current_user.full_name}]: {req.override_reason}"
        action = AuditAction.FINDING_OVERRIDDEN
    else:
        raise HTTPException(status_code=400, detail="Invalid decision. Must be CONFIRMED or OVERRIDDEN.")

    after_status = str(finding.status.value if hasattr(finding.status, "value") else finding.status)
    after_review = str(finding.review_status.value if hasattr(finding.review_status, "value") else finding.review_status)

    await audit_service.log_event(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=action,
        entity_type="FINDING",
        entity_id=finding.id,
        metadata_before={"status": before_status, "review_status": before_review},
        metadata_after={
            "status": after_status,
            "review_status": after_review,
            "override_reason": req.override_reason,
        },
    )

    await db.commit()
    await db.refresh(finding)

    f_read = FindingRead.model_validate(finding)
    if finding.requirement:
        f_read.requirement_title = finding.requirement.title
        f_read.requirement_category = finding.requirement.category
    if finding.evidence_clause:
        f_read.evidence_page_number = finding.evidence_clause.page_number
        f_read.evidence_section_title = finding.evidence_clause.section_title
    return f_read
