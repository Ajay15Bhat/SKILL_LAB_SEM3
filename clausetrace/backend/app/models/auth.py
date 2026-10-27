"""
ClauseTrace Multi-Tenant Organization and User RBAC Models.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, UserRole

if TYPE_CHECKING:
    from app.models.contract import Contract


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tenant boundary for data isolation.
    Contracts, versions, findings, and audit logs belong to an Organization.
    """
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[List["User"]] = relationship(
        "User", back_populates="organization", cascade="all, delete-orphan"
    )
    contracts: Mapped[List["Contract"]] = relationship(
        "Contract", back_populates="organization", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug} name={self.name}>"


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    User account with RBAC:
    - ADMIN: Organization management, requirements, approvals.
    - ANALYST: Uploads contracts, creates requirements, runs analyses, proposes obligations.
    - REVIEWER: Confirms/overrides findings, officially signs off/approves versions.
    - AUDITOR: Read-only access to permissible documents, findings, decisions, audit logs.
    """
    __tablename__ = "users"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        String(50),
        default=UserRole.ANALYST,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")
    contracts: Mapped[List["Contract"]] = relationship("Contract", back_populates="creator")

    __table_args__ = (
        Index("ix_users_org_role", "organization_id", "role"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
