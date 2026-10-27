"""
ClauseTrace FastAPI Application Entry Point.
Modular Monolith: REST API, OpenAPI docs, and native DB job queue.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1 import (
    audit,
    auth,
    comparisons,
    contracts,
    findings,
    jobs,
    obligations,
    requirements,
    versions,
)
from app.core.config import settings
from app.core.database import get_db, init_db
from app.core.security import get_current_user
from app.models.audit import AuditLog
from app.models.auth import User
from app.models.base import FindingStatus, JobStatus, ObligationStatus, VersionStatus
from app.models.contract import ContractVersion
from app.models.job import BackgroundJob
from app.models.obligation import Obligation
from app.models.requirement import Finding
from app.schemas import AuditLogRead

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clausetrace")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: bootstraps database schema and baseline demo data."""
    logger.info("Initializing ClauseTrace database and seed entities...")
    await init_db()
    logger.info("ClauseTrace engine initialized successfully.")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Evidence-Grounded Contract Change Impact & Obligation Tracking Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(contracts.router, prefix=settings.API_V1_STR)
app.include_router(versions.router, prefix=settings.API_V1_STR)
app.include_router(requirements.router, prefix=settings.API_V1_STR)
app.include_router(findings.router, prefix=settings.API_V1_STR)
app.include_router(comparisons.router, prefix=settings.API_V1_STR)
app.include_router(jobs.router, prefix=settings.API_V1_STR)
app.include_router(obligations.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", tags=["Health"])
async def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": settings.DATABASE_URL.split("://")[0],
    }


@app.get(f"{settings.API_V1_STR}/overview/metrics", tags=["Overview Dashboard"])
async def get_overview_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns live aggregated organizational metrics for the Overview Dashboard (Page 1).
    All data is computed in real time from database records.
    """
    org_id = current_user.organization_id

    # 1. Contracts awaiting review (DRAFT or IN_REVIEW versions)
    v_awaiting_stmt = select(func.count(ContractVersion.id)).where(
        ContractVersion.organization_id == org_id,
        ContractVersion.approval_status.in_([VersionStatus.DRAFT, VersionStatus.IN_REVIEW]),
    )
    v_awaiting = (await db.execute(v_awaiting_stmt)).scalar() or 0

    # 2. Approved versions
    v_approved_stmt = select(func.count(ContractVersion.id)).where(
        ContractVersion.organization_id == org_id,
        ContractVersion.approval_status == VersionStatus.APPROVED,
    )
    v_approved = (await db.execute(v_approved_stmt)).scalar() or 0

    # 3. Findings requiring attention (NOT_SATISFIED, NEEDS_REVIEW, PARTIALLY_SATISFIED)
    f_stmt = select(func.count(Finding.id)).where(
        Finding.organization_id == org_id,
        Finding.status.in_([
            FindingStatus.NOT_SATISFIED,
            FindingStatus.NEEDS_REVIEW,
            FindingStatus.PARTIALLY_SATISFIED,
        ]),
    )
    findings_needing_attention = (await db.execute(f_stmt)).scalar() or 0

    # 4. Processing jobs count
    j_stmt = select(func.count(BackgroundJob.id)).where(
        BackgroundJob.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING])
    )
    active_jobs = (await db.execute(j_stmt)).scalar() or 0

    # 5. Obligations metrics
    today = date.today()
    ob_total_stmt = select(func.count(Obligation.id)).where(
        Obligation.organization_id == org_id,
        Obligation.status != ObligationStatus.COMPLETED,
    )
    upcoming_obligations = (await db.execute(ob_total_stmt)).scalar() or 0

    ob_overdue_stmt = select(func.count(Obligation.id)).where(
        Obligation.organization_id == org_id,
        Obligation.status != ObligationStatus.COMPLETED,
        Obligation.due_date < today,
    )
    overdue_obligations = (await db.execute(ob_overdue_stmt)).scalar() or 0

    # 6. Recent audit events
    audit_stmt = (
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .where(AuditLog.organization_id == org_id)
        .order_by(AuditLog.created_at.desc())
        .limit(6)
    )
    recent_logs = (await db.execute(audit_stmt)).scalars().all()
    formatted_logs = []
    for l in recent_logs:
        r = AuditLogRead.model_validate(l)
        if l.user:
            r.actor_email = l.user.email
        formatted_logs.append(r)

    return {
        "contracts_awaiting_review": v_awaiting,
        "approved_versions_count": v_approved,
        "findings_requiring_attention": findings_needing_attention,
        "active_jobs_count": active_jobs,
        "upcoming_obligations_count": upcoming_obligations,
        "overdue_obligations_count": overdue_obligations,
        "recent_audit_events": formatted_logs,
    }
