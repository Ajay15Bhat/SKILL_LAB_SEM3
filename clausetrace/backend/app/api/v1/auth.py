"""
ClauseTrace Authentication & User Context API Endpoints.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.auth import Organization, User
from app.schemas import LoginRequest, LoginResponse, OrganizationRead, UserRead

router = APIRouter(prefix="/auth", tags=["Authentication & Tenancy"])


@router.get("/me", response_model=LoginResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns currently authenticated user and organization."""
    org_res = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
    org = org_res.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return LoginResponse(
        user=UserRead.model_validate(current_user),
        token=current_user.email,
        organization=OrganizationRead.model_validate(org),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate as a user by email (e.g. analyst@clausetrace.io or reviewer@clausetrace.io)."""
    email_clean = req.email.strip().lower()
    res = await db.execute(select(User).where(User.email == email_clean))
    user = res.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User '{req.email}' not found.",
        )

    org_res = await db.execute(select(Organization).where(Organization.id == user.organization_id))
    org = org_res.scalars().first()

    return LoginResponse(
        user=UserRead.model_validate(user),
        token=user.email,
        organization=OrganizationRead.model_validate(org),
    )


@router.get("/users", response_model=List[UserRead])
async def list_org_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists organization members for task assignment and role switching."""
    stmt = (
        select(User)
        .where(User.organization_id == current_user.organization_id)
        .order_by(User.full_name.asc())
    )
    res = await db.execute(stmt)
    return [UserRead.model_validate(u) for u in res.scalars().all()]
