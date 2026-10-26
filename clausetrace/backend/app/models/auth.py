"""
ClauseTrace User Model (Analyst vs Reviewer).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, UserRole

if TYPE_CHECKING:
    from app.models.contract import Contract


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    User account with RBAC:
    - ANALYST: Uploads contracts, creates requirements, inspects findings.
    - REVIEWER: Confirms/overrides findings, officially approves versions.
    """
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        String(50),
        default=UserRole.ANALYST,
        nullable=False,
    )

    contracts: Mapped[List["Contract"]] = relationship("Contract", back_populates="creator")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
