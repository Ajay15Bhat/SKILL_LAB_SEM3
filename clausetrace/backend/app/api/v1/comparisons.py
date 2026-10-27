"""
ClauseTrace Comparison / Version Diff Retrieval API Endpoints.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.auth import User
from app.models.diff import VersionDiff
from app.schemas import VersionDiffRead

router = APIRouter(prefix="/comparisons", tags=["Comparisons & Change Impact"])


@router.get("/{comparison_id}", response_model=VersionDiffRead)
async def get_comparison(
    comparison_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves an existing version comparison record."""
    stmt = select(VersionDiff).where(
        VersionDiff.id == comparison_id,
        VersionDiff.organization_id == current_user.organization_id,
    )
    res = await db.execute(stmt)
    diff = res.scalars().first()

    if not diff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comparison not found in your organization.",
        )
    return diff
