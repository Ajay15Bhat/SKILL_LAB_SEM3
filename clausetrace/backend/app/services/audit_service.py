"""
ClauseTrace Append-Only Audit Logging Service.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.base import AuditAction


class AuditService:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        organization_id: uuid.UUID,
        action: AuditAction,
        entity_type: str,
        entity_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        metadata_before: Optional[Dict[str, Any]] = None,
        metadata_after: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Appends an event to the immutable audit trail."""
        log = AuditLog(
            id=uuid.uuid4(),
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_before=metadata_before,
            metadata_after=metadata_after,
            ip_address=ip_address,
        )
        db.add(log)
        await db.flush()
        return log


audit_service = AuditService()
