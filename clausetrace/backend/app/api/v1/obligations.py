"""
ClauseTrace Contract Obligation Tracking API Endpoints.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.auth import User
from app.models.base import AuditAction, ObligationParty, ObligationStatus, UserRole
from app.models.contract import ContractVersion
from app.models.obligation import Obligation
from app.schemas import ObligationCreate, ObligationRead, ObligationUpdate
from app.services.audit_service import audit_service

router = APIRouter(prefix="/obligations", tags=["Obligations Tracking"])


@router.post("", response_model=ObligationRead, status_code=status.HTTP_201_CREATED)
async def create_obligation(
    req: ObligationCreate,
    current_user: User = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Creates an operational obligation tied to a contract version and supporting clause."""
    v_check = await db.execute(
        select(ContractVersion.id).where(
            ContractVersion.id == req.contract_version_id,
            ContractVersion.organization_id == current_user.organization_id,
        )
    )
    if not v_check.scalar():
        raise HTTPException(status_code=404, detail="Contract version not found in your organization.")

    obligation = Obligation(
        id=uuid.uuid4(),
        organization_id=current_user.organization_id,
        contract_version_id=req.contract_version_id,
        clause_id=req.clause_id,
        title=req.title,
        description=req.description,
        party=req.party,
        due_date=req.due_date,
        frequency=req.frequency,
        status=ObligationStatus.PENDING,
        assigned_to=req.assigned_to,
    )
    db.add(obligation)
    await db.flush()

    await audit_service.log_event(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.OBLIGATION_CREATED,
        entity_type="OBLIGATION",
        entity_id=obligation.id,
        metadata_after={"title": obligation.title, "party": obligation.party.value},
    )

    await db.commit()
    await db.refresh(obligation)
    return obligation


@router.get("", response_model=List[ObligationRead])
async def list_obligations(
    contract_version_id: Optional[uuid.UUID] = None,
    status_filter: Optional[ObligationStatus] = None,
    party_filter: Optional[ObligationParty] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists obligations with dynamic overdue calculation based on due_date.
    """
    stmt = (
        select(Obligation)
        .options(selectinload(Obligation.assignee))
        .where(Obligation.organization_id == current_user.organization_id)
        .order_by(Obligation.due_date.asc().nulls_last())
    )
    if contract_version_id:
        stmt = stmt.where(Obligation.contract_version_id == contract_version_id)
    if status_filter:
        stmt = stmt.where(Obligation.status == status_filter)
    if party_filter:
        stmt = stmt.where(Obligation.party == party_filter)

    res = await db.execute(stmt)
    obligations = res.scalars().all()

    today = date.today()
    output = []
    for o in obligations:
        o_read = ObligationRead.model_validate(o)
        if o.assignee:
            o_read.assignee_name = o.assignee.full_name
        # Consistent overdue check
        if o.due_date and o.due_date < today and o.status != ObligationStatus.COMPLETED:
            o_read.is_overdue = True
            if o_read.status != ObligationStatus.OVERDUE:
                o_read.status = ObligationStatus.OVERDUE
        output.append(o_read)
    return output


@router.patch("/{obligation_id}", response_model=ObligationRead)
async def update_obligation(
    obligation_id: uuid.UUID,
    req: ObligationUpdate,
    current_user: User = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN, UserRole.REVIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Updates obligation details, assignee, or execution status."""
    stmt = (
        select(Obligation)
        .options(selectinload(Obligation.assignee))
        .where(
            Obligation.id == obligation_id,
            Obligation.organization_id == current_user.organization_id,
        )
    )
    res = await db.execute(stmt)
    obligation = res.scalars().first()

    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found.")

    before_status = str(obligation.status.value if hasattr(obligation.status, "value") else obligation.status)

    if req.title is not None:
        obligation.title = req.title
    if req.description is not None:
        obligation.description = req.description
    if req.party is not None:
        obligation.party = req.party
    if req.due_date is not None:
        obligation.due_date = req.due_date
    if req.frequency is not None:
        obligation.frequency = req.frequency
    if req.status is not None:
        obligation.status = req.status
    if req.assigned_to is not None:
        obligation.assigned_to = req.assigned_to

    after_status = str(obligation.status.value if hasattr(obligation.status, "value") else obligation.status)

    await audit_service.log_event(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.OBLIGATION_STATUS_CHANGED,
        entity_type="OBLIGATION",
        entity_id=obligation.id,
        metadata_before={"status": before_status},
        metadata_after={"status": after_status},
    )

    await db.commit()
    await db.refresh(obligation)

    o_read = ObligationRead.model_validate(obligation)
    if obligation.assignee:
        o_read.assignee_name = obligation.assignee.full_name
    return o_read
