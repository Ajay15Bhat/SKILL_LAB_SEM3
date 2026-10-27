"""
ClauseTrace Contract, Immutable Version, and Extracted Clause Models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, VersionStatus

if TYPE_CHECKING:
    from app.models.approval import Approval
    from app.models.auth import Organization, User
    from app.models.obligation import Obligation
    from app.models.requirement import Finding


class Contract(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Contract container representing an enterprise vendor agreement.
    Holds multiple immutable revisions/versions over time.
    """
    __tablename__ = "contracts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contract_type: Mapped[str] = mapped_column(String(100), default="MSA", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="contracts")
    creator: Mapped[Optional["User"]] = relationship("User", back_populates="contracts", foreign_keys=[created_by])
    versions: Mapped[List["ContractVersion"]] = relationship(
        "ContractVersion",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ContractVersion.version_number.desc()",
    )

    __table_args__ = (
        Index("ix_contracts_org_vendor", "organization_id", "vendor_name"),
    )

    def __repr__(self) -> str:
        return f"<Contract id={self.id} title={self.title} vendor={self.vendor_name}>"


class ContractVersion(Base, UUIDPrimaryKeyMixin):
    """
    IMMUTABLE contract revision with cryptographic SHA-256 fingerprint.
    Approvals are strictly tied to this version ID and never silently inherited.
    """
    __tablename__ = "contract_versions"

    contract_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf", nullable=False)

    approval_status: Mapped[VersionStatus] = mapped_column(
        String(50),
        default=VersionStatus.DRAFT,
        nullable=False,
        index=True,
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
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
    approvals: Mapped[List["Approval"]] = relationship(
        "Approval", back_populates="version", cascade="all, delete-orphan",
        order_by="Approval.created_at.desc()",
    )
    obligations: Mapped[List["Obligation"]] = relationship(
        "Obligation", back_populates="version", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("contract_id", "version_number", name="uq_contract_version_number"),
        UniqueConstraint("contract_id", "sha256_checksum", name="uq_contract_sha256"),
        Index("ix_contract_versions_org_status", "organization_id", "approval_status"),
    )

    def __repr__(self) -> str:
        return f"<ContractVersion id={self.id} v={self.version_number} status={self.approval_status}>"


class Clause(Base, UUIDPrimaryKeyMixin):
    """
    Extracted textual clause/passage with page number and source character offsets.
    Evidence references in findings and obligations link back to this record.
    """
    __tablename__ = "clauses"

    contract_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contract_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    version: Mapped["ContractVersion"] = relationship("ContractVersion", back_populates="clauses")
    obligations: Mapped[List["Obligation"]] = relationship("Obligation", back_populates="clause")

    __table_args__ = (
        UniqueConstraint("contract_version_id", "clause_index", name="uq_version_clause_index"),
        Index("ix_clauses_version_page", "contract_version_id", "page_number"),
    )

    def __repr__(self) -> str:
        return f"<Clause id={self.id} idx={self.clause_index} p={self.page_number} sec={self.section_title}>"
