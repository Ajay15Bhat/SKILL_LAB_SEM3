"""
Audit Trail API Endpoints.
Provides the chronological history of all actions, uploads, diffs, and sign-offs.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/audit-trail", tags=["Audit Trail"])


@router.get("", response_model=List[AuditLogResponse])
async def get_audit_trail(
    entity_id: Optional[uuid.UUID] = Query(None, description="Filter by entity ID"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves the chronological audit ledger for the visual timeline.
    """
    conditions = []
    params = {"limit": limit}

    if entity_id:
        conditions.append("a.entity_id = :entity_id")
        params["entity_id"] = entity_id
    if entity_type:
        conditions.append("a.entity_type = :entity_type")
        params["entity_type"] = entity_type

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = text(f"""
        SELECT 
            a.id,
            a.action,
            a.entity_type,
            a.entity_id,
            a.details,
            u.full_name AS user_name,
            a.created_at
        FROM audit_logs a
        LEFT JOIN users u ON u.id = a.user_id
        {where_clause}
        ORDER BY a.created_at DESC
        LIMIT :limit;
    """)

    res = await db.execute(sql, params)
    rows = res.fetchall()

    return [
        AuditLogResponse(
            id=r[0],
            action=r[1],
            entity_type=r[2],
            entity_id=r[3],
            details=r[4] or {},
            user_name=r[5] or "System Worker",
            created_at=r[6],
        )
        for r in rows
    ]

