"""
ClauseTrace Background Job Queue Models.
Native PostgreSQL worker queue using 'FOR UPDATE SKIP LOCKED' (Zero Celery/Redis).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    JobStatus,
    JobType,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class BackgroundJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Native PostgreSQL-backed task queue table.
    Enables atomic lock and claim across distributed worker processes
    using `SELECT ... WHERE status = 'QUEUED' ORDER BY priority DESC, created_at ASC FOR UPDATE SKIP LOCKED`.
    """
    __tablename__ = "background_jobs"

    job_type: Mapped[JobType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    status: Mapped[JobStatus] = mapped_column(
        String(50),
        default=JobStatus.QUEUED,
        nullable=False,
        index=True,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )
    locked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    locked_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    __table_args__ = (
        # Optimized index for the worker queue's atomic claim query:
        Index(
            "ix_job_queue_claim",
            "status",
            "priority",
            "created_at",
            postgresql_where=(status == JobStatus.QUEUED),
        ),
    )

    def __repr__(self) -> str:
        return f"<BackgroundJob id={self.id} type={self.job_type} status={self.status} retries={self.retry_count}>"

