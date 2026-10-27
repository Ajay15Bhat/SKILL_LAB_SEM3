"""
ClauseTrace Background Processing Jobs API Endpoints.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.auth import User
from app.models.base import JobStatus
from app.models.job import BackgroundJob
from app.schemas import JobRead

router = APIRouter(prefix="/jobs", tags=["Background Processing"])


@router.get("/{job_id}", response_model=JobRead)
async def get_job_status(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Monitors async document extraction and processing progress."""
    stmt = select(BackgroundJob).where(BackgroundJob.id == job_id)
    res = await db.execute(stmt)
    job = res.scalars().first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    return job


@router.post("/{job_id}/retry", response_model=JobRead)
async def retry_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retries a failed background task."""
    stmt = select(BackgroundJob).where(BackgroundJob.id == job_id)
    res = await db.execute(stmt)
    job = res.scalars().first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status not in (JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot retry job in status '{job.status}'. Only FAILED jobs can be retried.",
        )

    job.status = JobStatus.QUEUED
    job.error_message = None
    job.retry_count += 1
    await db.commit()
    await db.refresh(job)
    return job
