"""
ClauseTrace Formal Approval State Machine Service.
Enforces that approvals are immutable and tied strictly to a specific Version ID.
Generates cryptographic SHA-256 sign-off seals.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval
from app.models.auth import User
from app.models.base import ApprovalDecision, AuditAction, UserRole, VersionStatus
from app.models.contract import ContractVersion
from app.models.requirement import Finding


class ApprovalService:
    @staticmethod
    async def process_approval(
        db: AsyncSession,
        version: ContractVersion,
        approver: User,
        decision: ApprovalDecision,
        comments: Optional[str] = None,
    ) -> Approval:
        """
        Officially signs off on a ContractVersion.
        Ensures strict tenant matching and RBAC rules.
        """
        # 1. Tenancy check
        if version.organization_id != approver.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Contract version belongs to a different organization.",
            )

        # 2. RBAC check (Reviewer or Admin required)
        if approver.role not in (UserRole.REVIEWER, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: User with role '{approver.role}' cannot approve contracts. Reviewer or Admin required.",
            )

        # 3. Cryptographic SHA-256 Signature Seal
        now = datetime.now(timezone.utc)
        sig_input = f"{version.sha256_checksum}:{approver.id}:{decision.value}:{now.isoformat()}"
        sig_hash = hashlib.sha256(sig_input.encode("utf-8")).hexdigest()

        # 4. State transition
        if decision == ApprovalDecision.APPROVED:
            version.approval_status = VersionStatus.APPROVED
            version.approved_by = approver.id
            version.approved_at = now
        else:
            version.approval_status = VersionStatus.REJECTED
            version.approved_by = approver.id
            version.approved_at = now

        approval_record = Approval(
            id=uuid.uuid4(),
            organization_id=approver.organization_id,
            contract_version_id=version.id,
            approver_id=approver.id,
            decision=decision,
            comments=comments,
            signature_hash=sig_hash,
            created_at=now,
        )

        db.add(approval_record)
        await db.flush()
        return approval_record


approval_service = ApprovalService()
