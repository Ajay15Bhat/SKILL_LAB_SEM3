"""
ClauseTrace Obligation Tracking Models.
Tracks operational commitments and covenants tied to specific clauses and versions.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    ObligationFrequency,
    ObligationParty,
    ObligationStatus,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from app.models.auth import Organization, User
    from app.models.contract import Clause, ContractVersion


class Obligation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Contractual obligation extracted from or assigned to a contract clause/version.
    Lifecycle: PENDING -> IN_PROGRESS -> COMPLETED (or OVERDUE if past due_date).
    """
    __tablename__ = "obligations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contract_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("clauses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    party: Mapped[ObligationParty] = mapped_column(
        String(50),
        default=ObligationParty.VENDOR,
        nullable=False,
    )
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    frequency: Mapped[ObligationFrequency] = mapped_column(
        String(50),
        default=ObligationFrequency.ONE_TIME,
        nullable=False,
    )
    status: Mapped[ObligationStatus] = mapped_column(
        String(50),
        default=ObligationStatus.PENDING,
        nullable=False,
        index=True,
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    version: Mapped["ContractVersion"] = relationship("ContractVersion", back_populates="obligations")
    clause: Mapped[Optional["Clause"]] = relationship("Clause", back_populates="obligations")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to])

    __table_args__ = (
        Index("ix_obligations_version_status", "contract_version_id", "status"),
        Index("ix_obligations_org_due", "organization_id", "due_date"),
    )

    def __repr__(self) -> str:
        return f"<Obligation id={self.id} title={self.title} status={self.status} due={self.due_date}>"
