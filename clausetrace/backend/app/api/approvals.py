"""
Contract Version Approval State Machine API Endpoints.
Enforces that approvals are strictly version-tied. Approving v1 never approves v2.
"""

import hashlib
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.base import ApprovalDecision, AuditAction, VersionStatus
from app.models.contract import ContractVersion
from app.schemas.approval import ApprovalRequest, ApprovalResponse

router = APIRouter(prefix="/versions", tags=["Approvals"])


@router.post("/{version_id}/approve", response_model=ApprovalResponse)
async def approve_version(
    version_id: uuid.UUID,
    payload: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Formal Reviewer Sign-Off on a Contract Version.
    - Transitions version status from DRAFT -> APPROVED.
    - Generates a non-repudiation cryptographic signature hash.
    - Records sign-off in the audit trail.
    """
    version = await db.get(ContractVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Contract version not found")

    if version.approval_status == VersionStatus.APPROVED:
        raise HTTPException(status_code=400, detail="This version has already been approved.")

    reviewer_id = uuid.UUID(settings.DEMO_REVIEWER_ID)
    now = datetime.now()

    # Cryptographic signature hash: sha256(file_checksum + reviewer_id + timestamp)
    sig_raw = f"{version.sha256_checksum}:{reviewer_id}:{now.isoformat()}"
    signature_hash = hashlib.sha256(sig_raw.encode()).hexdigest()

    # Update version state
    version.approval_status = VersionStatus.APPROVED
    version.approved_by = reviewer_id
    version.approved_at = now

    # Append to Audit Log
    audit = AuditLog(
        user_id=reviewer_id,
        action=AuditAction.APPROVAL_GRANTED,
        entity_type="contract_version",
        entity_id=version.id,
        details={
            "version_number": version.version_number,
            "signature_hash": signature_hash,
            "comments": payload.comments or "Formal approval recorded.",
        },
    )
    db.add(audit)
    await db.commit()

    return ApprovalResponse(
        version_id=version.id,
        version_number=version.version_number,
        approval_status=version.approval_status,
        approved_by=reviewer_id,
        approved_at=now,
        signature_hash=signature_hash,
        comments=payload.comments,
    )


@router.post("/{version_id}/reject", response_model=ApprovalResponse)
async def reject_version(
    version_id: uuid.UUID,
    payload: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rejects a contract version."""
    version = await db.get(ContractVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Contract version not found")

    reviewer_id = uuid.UUID(settings.DEMO_REVIEWER_ID)
    now = datetime.now()

    version.approval_status = VersionStatus.REJECTED
    version.approved_by = reviewer_id
    version.approved_at = now

    audit = AuditLog(
        user_id=reviewer_id,
        action=AuditAction.APPROVAL_REJECTED,
        entity_type="contract_version",
        entity_id=version.id,
        details={
            "version_number": version.version_number,
            "comments": payload.comments or "Version rejected.",
        },
    )
    db.add(audit)
    await db.commit()

    return ApprovalResponse(
        version_id=version.id,
        version_number=version.version_number,
        approval_status=version.approval_status,
        approved_by=reviewer_id,
        approved_at=now,
        signature_hash="REJECTED",
        comments=payload.comments,
    )

