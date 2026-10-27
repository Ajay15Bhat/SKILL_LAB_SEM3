"""
Contract Version Diffing & Change Impact API Endpoint.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.base import AuditAction
from app.models.contract import ContractVersion
from app.schemas.diff import DiffResponse
from app.services.differ import ContractDifferService

router = APIRouter(prefix="/contracts", tags=["Diffing & Change Impact"])


@router.get("/{contract_id}/diff", response_model=DiffResponse)
async def get_version_diff(
    contract_id: uuid.UUID,
    source_version_id: uuid.UUID = Query(..., description="Base version ID (e.g. v1)"),
    target_version_id: uuid.UUID = Query(..., description="New revision version ID (e.g. v2)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Compares two contract versions:
    - Returns clause-by-clause visual differences (added, removed, modified).
    - Identifies which compliance requirements are impacted by modified clauses.
    - Flags impacted requirements in target version for mandatory re-review.
    """
    # 1. Verify both versions exist and belong to the contract
    v1 = await db.get(ContractVersion, source_version_id)
    v2 = await db.get(ContractVersion, target_version_id)
    if not v1 or not v2:
        raise HTTPException(status_code=404, detail="One or both contract versions not found")
    if v1.contract_id != contract_id or v2.contract_id != contract_id:
        raise HTTPException(status_code=400, detail="Versions do not belong to the specified contract")

    # 2. Compute diff and change impact
    diff_result = await ContractDifferService.compute_version_diff(
        source_version_id=source_version_id,
        target_version_id=target_version_id,
        db=db,
    )

    # 3. Log diff generation in audit trail
    audit = AuditLog(
        user_id=uuid.UUID(settings.DEMO_ANALYST_ID),
        action=AuditAction.DIFF_GENERATED,
        entity_type="contract_version",
        entity_id=target_version_id,
        details={
            "source_v": v1.version_number,
            "target_v": v2.version_number,
            "modifications": diff_result.metrics["modifications"],
            "impacted_requirements": len(diff_result.impacted_requirements),
        },
    )
    db.add(audit)
    await db.commit()

    return diff_result

