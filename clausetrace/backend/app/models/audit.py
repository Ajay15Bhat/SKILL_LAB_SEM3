"""
ClauseTrace Audit Trail Model.
Append-only log for the visual audit timeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditAction, Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.auth import User


class AuditLog(Base, UUIDPrimaryKeyMixin):
    """
    Append-only audit trail capturing all uploads, evaluations, and reviewer actions.
    """
    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[AuditAction] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    user: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} entity={self.entity_type}:{self.entity_id}>"
