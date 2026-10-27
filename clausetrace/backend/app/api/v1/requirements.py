"""
ClauseTrace Requirements Management API Endpoints.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.auth import User
from app.models.base import AuditAction, UserRole
from app.models.requirement import Requirement
from app.schemas import RequirementCreate, RequirementRead, RequirementUpdate
from app.services.audit_service import audit_service

router = APIRouter(prefix="/requirements", tags=["Requirements & Policies"])


@router.post("", response_model=RequirementRead, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    req: RequirementCreate,
    current_user: User = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new compliance review requirement / policy rule."""
    requirement = Requirement(
        id=uuid.uuid4(),
        organization_id=current_user.organization_id,
        contract_id=req.contract_id,
        title=req.title,
        category=req.category,
        description=req.description,
        search_keywords=req.search_keywords,
        is_mandatory=req.is_mandatory,
        created_by=current_user.id,
    )
    db.add(requirement)
    await db.flush()

    await audit_service.log_event(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.REQUIREMENT_CREATED,
        entity_type="REQUIREMENT",
        entity_id=requirement.id,
        metadata_after={"title": requirement.title, "category": requirement.category},
    )

    await db.commit()
    await db.refresh(requirement)
    return requirement


@router.get("", response_model=List[RequirementRead])
async def list_requirements(
    contract_id: Optional[uuid.UUID] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists compliance requirements for the organization."""
    stmt = (
        select(Requirement)
        .where(Requirement.organization_id == current_user.organization_id)
        .order_by(Requirement.created_at.desc())
    )
    if contract_id:
        stmt = stmt.where((Requirement.contract_id == None) | (Requirement.contract_id == contract_id))
    if category:
        stmt = stmt.where(Requirement.category == category)

    res = await db.execute(stmt)
    return res.scalars().all()


@router.patch("/{requirement_id}", response_model=RequirementRead)
async def update_requirement(
    requirement_id: uuid.UUID,
    req: RequirementUpdate,
    current_user: User = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Updates an existing requirement."""
    stmt = select(Requirement).where(
        Requirement.id == requirement_id,
        Requirement.organization_id == current_user.organization_id,
    )
    res = await db.execute(stmt)
    requirement = res.scalars().first()

    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found.")

    before_meta = {"title": requirement.title, "category": requirement.category}

    if req.title is not None:
        requirement.title = req.title
    if req.category is not None:
        requirement.category = req.category
    if req.description is not None:
        requirement.description = req.description
    if req.search_keywords is not None:
        requirement.search_keywords = req.search_keywords
    if req.is_mandatory is not None:
        requirement.is_mandatory = req.is_mandatory

    await audit_service.log_event(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.REQUIREMENT_UPDATED,
        entity_type="REQUIREMENT",
        entity_id=requirement.id,
        metadata_before=before_meta,
        metadata_after={"title": requirement.title, "category": requirement.category},
    )

    await db.commit()
    await db.refresh(requirement)
    return requirement
