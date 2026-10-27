"""
Requirements & Compliance Findings API Endpoints.
Guarantees 'No Silent Inheritance': every version requires distinct findings.
"""

import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.base import AuditAction, ReviewStatus
from app.models.contract import ContractVersion
from app.models.requirement import Finding, Requirement
from app.schemas.requirement import (
    FindingOverrideRequest,
    FindingResponse,
    RequirementCreate,
    RequirementResponse,
)
from app.services.search import HybridEvaluationService

router = APIRouter(tags=["Requirements & Findings"])


@router.post("/requirements", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    payload: RequirementCreate,
    db: AsyncSession = Depends(get_db),
):
    """Creates a new compliance requirement rule."""
    req = Requirement(
        title=payload.title,
        category=payload.category,
        description=payload.description,
        search_keywords=payload.search_keywords,
        is_mandatory=payload.is_mandatory,
        created_by=uuid.UUID(settings.DEMO_ANALYST_ID),
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    audit = AuditLog(
        user_id=uuid.UUID(settings.DEMO_ANALYST_ID),
        action=AuditAction.REQUIREMENT_CREATED,
        entity_type="requirement",
        entity_id=req.id,
        details={"title": req.title, "category": req.category},
    )
    db.add(audit)
    await db.commit()

    return req


@router.get("/requirements", response_model=List[RequirementResponse])
async def list_requirements(db: AsyncSession = Depends(get_db)):
    """Lists all registered requirements."""
    res = await db.execute(select(Requirement).order_by(Requirement.created_at.asc()))
    return res.scalars().all()


@router.post("/versions/{version_id}/evaluate", response_model=List[FindingResponse])
async def evaluate_version_requirements(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers hybrid compliance evaluation for a specific contract version.
    Deterministic FTS + Gemini Flash.
    """
    version = await db.get(ContractVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Contract version not found")

    findings = await HybridEvaluationService.evaluate_version(
        contract_version_id=version_id,
        db=db,
    )
    await db.commit()

    # Re-query to get joined fields
    return await get_version_findings(version_id, db)


@router.get("/versions/{version_id}/findings", response_model=List[FindingResponse])
async def get_version_findings(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves all findings tied to this specific version."""
    sql = text("""
        SELECT 
            f.id,
            f.requirement_id,
            r.title AS requirement_title,
            f.contract_version_id,
            f.status,
            f.evidence_clause_id,
            c.page_number AS clause_page,
            f.evidence_quote,
            f.confidence_score,
            f.analysis_notes,
            f.review_status,
            f.reviewed_at,
            f.created_at
        FROM findings f
        JOIN requirements r ON r.id = f.requirement_id
        LEFT JOIN clauses c ON c.id = f.evidence_clause_id
        WHERE f.contract_version_id = :vid
        ORDER BY r.created_at ASC;
    """)
    res = await db.execute(sql, {"vid": version_id})
    rows = res.fetchall()

    return [
        FindingResponse(
            id=r[0],
            requirement_id=r[1],
            requirement_title=r[2],
            contract_version_id=r[3],
            status=r[4],
            evidence_clause_id=r[5],
            clause_page=r[6],
            evidence_quote=r[7],
            confidence_score=r[8],
            analysis_notes=r[9],
            review_status=r[10],
            reviewed_at=r[11],
            created_at=r[12],
        )
        for r in rows
    ]


@router.patch("/findings/{finding_id}", response_model=FindingResponse)
async def review_or_override_finding(
    finding_id: uuid.UUID,
    payload: FindingOverrideRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Human-in-the-Loop Reviewer Sign-Off or Override on an AI Finding.
    """
    finding = await db.get(Finding, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    old_status = finding.status
    finding.status = payload.status
    finding.review_status = ReviewStatus.OVERRIDDEN if old_status != payload.status else ReviewStatus.CONFIRMED
    finding.analysis_notes = payload.analysis_notes or finding.analysis_notes
    finding.reviewed_by = uuid.UUID(settings.DEMO_REVIEWER_ID)
    finding.reviewed_at = datetime.now()

    # Log to audit trail
    action = AuditAction.FINDING_OVERRIDDEN if old_status != payload.status else AuditAction.FINDING_CONFIRMED
    audit = AuditLog(
        user_id=uuid.UUID(settings.DEMO_REVIEWER_ID),
        action=action,
        entity_type="finding",
        entity_id=finding.id,
        details={
            "old_status": old_status,
            "new_status": finding.status,
            "review_notes": finding.analysis_notes,
        },
    )
    db.add(audit)
    await db.commit()

    return await get_single_finding(finding.id, db)


async def get_single_finding(finding_id: uuid.UUID, db: AsyncSession) -> FindingResponse:
    sql = text("""
        SELECT 
            f.id, f.requirement_id, r.title, f.contract_version_id, f.status,
            f.evidence_clause_id, c.page_number, f.evidence_quote, f.confidence_score,
            f.analysis_notes, f.review_status, f.reviewed_at, f.created_at
        FROM findings f
        JOIN requirements r ON r.id = f.requirement_id
        LEFT JOIN clauses c ON c.id = f.evidence_clause_id
        WHERE f.id = :fid;
    """)
    res = await db.execute(sql, {"fid": finding_id})
    r = res.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Finding not found")
    return FindingResponse(
        id=r[0], requirement_id=r[1], requirement_title=r[2], contract_version_id=r[3],
        status=r[4], evidence_clause_id=r[5], clause_page=r[6], evidence_quote=r[7],
        confidence_score=r[8], analysis_notes=r[9], review_status=r[10],
        reviewed_at=r[11], created_at=r[12],
    )

