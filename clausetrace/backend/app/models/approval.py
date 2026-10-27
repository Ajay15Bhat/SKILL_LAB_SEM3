"""
ClauseTrace Approval State Machine Models.
Approvals are strictly immutable and tied to a single version_id.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ApprovalDecision, Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.auth import Organization, User
    from app.models.contract import ContractVersion


class Approval(Base, UUIDPrimaryKeyMixin):
    """
    Formal sign-off on a specific ContractVersion.
    Strict rule: Approving v1 only approves v1. v2 starts in DRAFT and requires its own approval.
    """
    __tablename__ = "approvals"

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
    approver_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    decision: Mapped[ApprovalDecision] = mapped_column(
        String(50),
        default=ApprovalDecision.APPROVED,
        nullable=False,
    )
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signature_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Cryptographic SHA-256 seal combining version checksum, user ID, decision, and timestamp."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    version: Mapped["ContractVersion"] = relationship("ContractVersion", back_populates="approvals")
    approver: Mapped["User"] = relationship("User")

    __table_args__ = (
        Index("ix_approvals_version_decision", "contract_version_id", "decision"),
    )

    def __repr__(self) -> str:
        return f"<Approval id={self.id} version={self.contract_version_id} decision={self.decision}>"
