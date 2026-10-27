"""
ClauseTrace Version Diffing and Change Impact Models.
Stores deterministic clause-by-clause diffs and flags requirements for reassessment.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    JSON,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.auth import Organization
    from app.models.contract import ContractVersion


class VersionDiff(Base, UUIDPrimaryKeyMixin):
    """
    Deterministic comparison between two contract versions (e.g., v1 -> v2).
    Contains granular text diffs, clause modifications, and impacted requirement flags.
    """
    __tablename__ = "version_diffs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contract_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contract_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    diff_summary: Mapped[str] = mapped_column(Text, nullable=False)
    diff_payload: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    source_version: Mapped["ContractVersion"] = relationship(
        "ContractVersion", foreign_keys=[source_version_id]
    )
    target_version: Mapped["ContractVersion"] = relationship(
        "ContractVersion", foreign_keys=[target_version_id]
    )

    __table_args__ = (
        UniqueConstraint("source_version_id", "target_version_id", name="uq_version_diff_pair"),
        Index("ix_version_diffs_target", "target_version_id"),
    )

    def __repr__(self) -> str:
        return f"<VersionDiff id={self.id} {self.source_version_id} -> {self.target_version_id}>"
