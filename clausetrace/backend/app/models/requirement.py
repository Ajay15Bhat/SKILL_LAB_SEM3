"""
ClauseTrace Requirements and Evidence-Grounded Findings.
Enforces 'No Silent Inheritance': findings are strictly tied to a specific version.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    FindingStatus,
    ReviewStatus,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.contract import Clause, ContractVersion


class Requirement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Review requirement / policy rule (e.g. 'Must have 30-day notice for termination').
    """
    __tablename__ = "requirements"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="General", nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    search_keywords: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    findings: Mapped[List["Finding"]] = relationship(
        "Finding", back_populates="requirement", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Requirement id={self.id} title={self.title} cat={self.category}>"


class Finding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Finding evaluating a Requirement against a specific ContractVersion.
    NEVER silently inherited across versions. Each version requires fresh evaluation.
    """
    __tablename__ = "findings"

    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contract_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[FindingStatus] = mapped_column(
        String(50),
        default=FindingStatus.NEEDS_REVIEW,
        nullable=False,
        index=True,
    )
    evidence_clause_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clauses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    evidence_quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    analysis_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_status: Mapped[ReviewStatus] = mapped_column(
        String(50), default=ReviewStatus.PROPOSED, nullable=False
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    requirement: Mapped["Requirement"] = relationship("Requirement", back_populates="findings")
    version: Mapped["ContractVersion"] = relationship("ContractVersion", back_populates="findings")
    evidence_clause: Mapped[Optional["Clause"]] = relationship("Clause")
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (
        UniqueConstraint("requirement_id", "contract_version_id", name="uq_req_ver_finding"),
    )

    def __repr__(self) -> str:
        return f"<Finding id={self.id} req={self.requirement_id} ver={self.contract_version_id} status={self.status}>"
