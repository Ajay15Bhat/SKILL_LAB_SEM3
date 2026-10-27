"""
ClauseTrace Requirements and Evidence-Grounded Findings.
Enforces 'No Silent Inheritance': findings are strictly tied to a specific version.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    FindingStatus,
    ReviewStatus,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from app.models.auth import Organization, User
    from app.models.contract import Clause, Contract, ContractVersion


class Requirement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Review requirement / policy rule (e.g. 'The termination notice period must not exceed 30 days').
    Can be scoped to an organization or a specific contract.
    """
    __tablename__ = "requirements"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="General", nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    search_keywords: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    findings: Mapped[List["Finding"]] = relationship(
        "Finding", back_populates="requirement", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_requirements_org_cat", "organization_id", "category"),
    )

    def __repr__(self) -> str:
        return f"<Requirement id={self.id} title={self.title} cat={self.category}>"


class Finding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Evidence-backed Finding evaluating a Requirement against a specific ContractVersion.
    CRUCIAL: NEVER silently inherited across versions. Each version requires fresh evaluation.
    """
    __tablename__ = "findings"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
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
        Uuid(as_uuid=True),
        ForeignKey("clauses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    evidence_quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    analysis_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_by: Mapped[str] = mapped_column(String(50), default="DETERMINISTIC_SEARCH", nullable=False)

    review_status: Mapped[ReviewStatus] = mapped_column(
        String(50), default=ReviewStatus.PROPOSED, nullable=False
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
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
        UniqueConstraint("requirement_id", "contract_version_id", name="uq_requirement_version_finding"),
        Index("ix_findings_version_status", "contract_version_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Finding id={self.id} req={self.requirement_id} ver={self.contract_version_id} status={self.status}>"
