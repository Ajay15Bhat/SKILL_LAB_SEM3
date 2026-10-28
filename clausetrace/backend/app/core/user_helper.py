"""
ClauseTrace User Seeding Helper.
Ensures demo accounts (Analyst & Reviewer) exist to prevent foreign key errors.
"""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.auth import User
from app.models.base import UserRole


async def ensure_demo_users(db: AsyncSession) -> None:
    """Ensures Analyst and Reviewer demo accounts exist in the database."""
    try:
        analyst_id = uuid.UUID(settings.DEMO_ANALYST_ID)
        reviewer_id = uuid.UUID(settings.DEMO_REVIEWER_ID)

        analyst = await db.get(User, analyst_id)
        if not analyst:
            db.add(User(
                id=analyst_id,
                email="analyst@clausetrace.io",
                full_name="Alex Analyst",
                role=UserRole.ANALYST,
            ))

        reviewer = await db.get(User, reviewer_id)
        if not reviewer:
            db.add(User(
                id=reviewer_id,
                email="reviewer@clausetrace.io",
                full_name="Rachel Reviewer",
                role=UserRole.REVIEWER,
            ))

        await db.flush()
    except Exception:
        # If already exists or concurrent insertion, ignore
        pass

