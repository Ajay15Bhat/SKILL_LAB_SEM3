"""
ClauseTrace Database Engine, Session Factory, and Initializer.
"""

from __future__ import annotations

import logging
import uuid
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models.auth import Organization, User
from app.models.base import Base, UserRole
from app.models.requirement import Requirement

logger = logging.getLogger(__name__)

# Engine configuration
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {}
if is_sqlite:
    connect_args["check_same_thread"] = False
else:
    connect_args["timeout"] = 15

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an isolated async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


DEMO_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ANALYST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
REVIEWER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
ADMIN_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000004")
AUDITOR_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000005")


async def init_db() -> None:
    """Initializes tables and seeds initial organization, users, and baseline requirements."""
    async with engine.begin() as conn:
        # Create all tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)

    # Seed baseline records if not present
    async with AsyncSessionLocal() as session:
        # 1. Seed Organization
        result = await session.execute(
            select(Organization).where(Organization.id == DEMO_ORG_ID)
        )
        org = result.scalars().first()
        if not org:
            org = Organization(
                id=DEMO_ORG_ID,
                name="Acme Enterprise Corp",
                slug="acme-corp",
                is_active=True,
            )
            session.add(org)
            await session.flush()

        # 2. Seed Users
        users_to_seed = [
            (
                ANALYST_USER_ID,
                "analyst@clausetrace.io",
                "Alex Analyst",
                UserRole.ANALYST,
            ),
            (
                REVIEWER_USER_ID,
                "reviewer@clausetrace.io",
                "Rachel Reviewer",
                UserRole.REVIEWER,
            ),
            (
                ADMIN_USER_ID,
                "admin@clausetrace.io",
                "Aaron Admin",
                UserRole.ADMIN,
            ),
            (
                AUDITOR_USER_ID,
                "auditor@clausetrace.io",
                "Audrey Auditor",
                UserRole.AUDITOR,
            ),
        ]

        for user_id, email, name, role in users_to_seed:
            res = await session.execute(select(User).where(User.email == email))
            existing_user = res.scalars().first()
            if not existing_user:
                new_user = User(
                    id=user_id,
                    organization_id=DEMO_ORG_ID,
                    email=email,
                    full_name=name,
                    role=role,
                    is_active=True,
                )
                session.add(new_user)

        await session.flush()

        # 3. Seed baseline requirements (acceptance test requirement included)
        req_res = await session.execute(
            select(Requirement).where(Requirement.organization_id == DEMO_ORG_ID)
        )
        existing_reqs = req_res.scalars().all()
        if not existing_reqs:
            baseline_reqs = [
                Requirement(
                    id=uuid.uuid4(),
                    organization_id=DEMO_ORG_ID,
                    title="Termination Notice Limit (Max 30 Days)",
                    category="Termination and notice periods",
                    description="The termination notice period must not exceed 30 days. Any requirement of 60 days or more notice is non-compliant.",
                    search_keywords=["termination", "notice", "days", "written notice", "terminate"],
                    is_mandatory=True,
                    created_by=ANALYST_USER_ID,
                ),
                Requirement(
                    id=uuid.uuid4(),
                    organization_id=DEMO_ORG_ID,
                    title="Standard Payment Terms (Net 30)",
                    category="Payment terms",
                    description="Payment terms must provide at least 30 days from receipt of a valid undisputed invoice.",
                    search_keywords=["payment", "invoice", "net 30", "due", "fees"],
                    is_mandatory=True,
                    created_by=ANALYST_USER_ID,
                ),
                Requirement(
                    id=uuid.uuid4(),
                    organization_id=DEMO_ORG_ID,
                    title="Confidentiality Survival Period",
                    category="Confidentiality",
                    description="Confidentiality and non-disclosure obligations must survive termination or expiration for a minimum of 3 years.",
                    search_keywords=["confidentiality", "proprietary", "survival", "survive", "disclosure"],
                    is_mandatory=True,
                    created_by=ANALYST_USER_ID,
                ),
                Requirement(
                    id=uuid.uuid4(),
                    organization_id=DEMO_ORG_ID,
                    title="Liability and Indemnification Protection",
                    category="Liability and indemnification",
                    description="Vendor must indemnify customer against third-party IP infringement without an aggregate liability cap.",
                    search_keywords=["indemnify", "indemnification", "liability", "infringement", "damages"],
                    is_mandatory=True,
                    created_by=ANALYST_USER_ID,
                ),
            ]
            for req in baseline_reqs:
                session.add(req)

        await session.commit()
