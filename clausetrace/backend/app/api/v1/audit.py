"""
ClauseTrace Organization-Wide Audit Trail API Endpoints.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.audit import AuditLog
from app.models.auth import User
from app.models.base import AuditAction
from app.schemas import AuditLogRead

router = APIRouter(prefix="/audit-events", tags=["Audit Trail"])


@router.get("", response_model=List[AuditLogRead])
async def list_audit_events(
    action: Optional[AuditAction] = None,
    entity_type: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns an append-only timeline of all operations performed within the organization.
    """
    stmt = (
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .where(AuditLog.organization_id == current_user.organization_id)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)

    res = await db.execute(stmt)
    logs = res.scalars().all()

    output = []
    for l in logs:
        r = AuditLogRead.model_validate(l)
        if l.user:
            r.actor_email = l.user.email
        output.append(r)
    return output
