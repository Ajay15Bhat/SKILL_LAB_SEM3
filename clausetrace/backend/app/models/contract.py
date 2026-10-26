"""
ClauseTrace Contract, Immutable Version, and Clause Models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, VersionStatus

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.requirement import Finding


class Contract(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Contract container representing an enterprise agreement relationship.
    Holds multiple immutable revisions/versions over time.
    """
    __tablename__ = "contracts"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contract_type: Mapped[str] = mapped_column(String(100), default="MSA", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    creator: Mapped[Optional["User"]] = relationship("User", back_populates="contracts")
    versions: Mapped[List["ContractVersion"]] = relationship(
        "ContractVersion",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ContractVersion.version_number.desc()",
    )

    def __repr__(self) -> str:
        return f"<Contract id={self.id} title={self.title} vendor={self.vendor_name}>"


class ContractVersion(Base, UUIDPrimaryKeyMixin):
    """
    IMMUTABLE contract revision with SHA-256 fingerprint.
    Approvals are strictly tied to this version ID.
    """
    __tablename__ = "contract_versions"

    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    approval_status: Mapped[VersionStatus] = mapped_column(
        String(50),
        default=VersionStatus.DRAFT,
        nullable=False,
        index=True,
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    contract: Mapped["Contract"] = relationship("Contract", back_populates="versions")
    clauses: Mapped[List["Clause"]] = relationship(
        "Clause",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="Clause.clause_index.asc()",
    )
    findings: Mapped[List["Finding"]] = relationship(
        "Finding", back_populates="version", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("contract_id", "version_number", name="uq_contract_version"),
        UniqueConstraint("contract_id", "sha256_checksum", name="uq_contract_sha256"),
    )

    def __repr__(self) -> str:
        return f"<ContractVersion id={self.id} v={self.version_number} status={self.approval_status}>"


class Clause(Base, UUIDPrimaryKeyMixin):
    """
    Extracted textual clause/chunk with page number and PostgreSQL tsvector.
    """
    __tablename__ = "clauses"

    contract_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contract_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    search_vector: Mapped[Optional[object]] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', coalesce(section_title, '') || ' ' || text_content)",
            persisted=True,
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    version: Mapped["ContractVersion"] = relationship("ContractVersion", back_populates="clauses")

    __table_args__ = (
        UniqueConstraint("contract_version_id", "clause_index", name="uq_version_clause_index"),
        Index("ix_clauses_fts", "search_vector", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Clause id={self.id} idx={self.clause_index} p={self.page_number}>"
