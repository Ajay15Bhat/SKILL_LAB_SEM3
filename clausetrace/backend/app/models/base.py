"""
ClauseTrace Base Model, Enums, and Shared Mixins.
SQLAlchemy 2.x declarative base and domain enums with SQLite & PostgreSQL cross-compatibility.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

POSTGRES_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=POSTGRES_NAMING_CONVENTION)


class TimestampMixin:
    """Provides created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """Provides a cross-platform UUID v4 primary key."""
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


# ============================================================================
# DOMAIN ENUMS
# ============================================================================

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    REVIEWER = "REVIEWER"
    AUDITOR = "AUDITOR"


class VersionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(str, enum.Enum):
    EXTRACT_DOCUMENT = "EXTRACT_DOCUMENT"
    GENERATE_DIFF = "GENERATE_DIFF"
    EVALUATE_REQUIREMENTS = "EVALUATE_REQUIREMENTS"
    REINDEX_SEARCH = "REINDEX_SEARCH"


class FindingStatus(str, enum.Enum):
    SATISFIED = "SATISFIED"
    PARTIALLY_SATISFIED = "PARTIALLY_SATISFIED"
    NOT_SATISFIED = "NOT_SATISFIED"
    NOT_FOUND = "NOT_FOUND"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ReviewStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"
    OVERRIDDEN = "OVERRIDDEN"


class ApprovalDecision(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ObligationStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"


class ObligationParty(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"
    MUTUAL = "MUTUAL"


class ObligationFrequency(str, enum.Enum):
    ONE_TIME = "ONE_TIME"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"


class AuditAction(str, enum.Enum):
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    VERSION_CREATED = "VERSION_CREATED"
    VERSION_STATUS_CHANGED = "VERSION_STATUS_CHANGED"
    REQUIREMENT_CREATED = "REQUIREMENT_CREATED"
    REQUIREMENT_UPDATED = "REQUIREMENT_UPDATED"
    REQUIREMENT_EVALUATED = "REQUIREMENT_EVALUATED"
    FINDING_CONFIRMED = "FINDING_CONFIRMED"
    FINDING_OVERRIDDEN = "FINDING_OVERRIDDEN"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    OBLIGATION_CREATED = "OBLIGATION_CREATED"
    OBLIGATION_STATUS_CHANGED = "OBLIGATION_STATUS_CHANGED"
    DIFF_GENERATED = "DIFF_GENERATED"
