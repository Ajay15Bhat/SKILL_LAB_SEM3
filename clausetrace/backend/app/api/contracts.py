"""
Contract & Version Management API Endpoints.
Handles PDF file uploads, SHA-256 fingerprinting, and version tracking.
"""

import hashlib
import os
import uuid
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.base import AuditAction, VersionStatus
from app.models.contract import Clause, Contract, ContractVersion
from app.schemas.contract import ClauseResponse, ContractCreate, ContractResponse, VersionResponse
from app.services.extractor import PDFExtractorService
from app.services.search import HybridEvaluationService

router = APIRouter(prefix="/contracts", tags=["Contracts & Versions"])


@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    payload: ContractCreate,
    db: AsyncSession = Depends(get_db),
):
    """Creates a new contract container."""
    contract = Contract(
        title=payload.title,
        vendor_name=payload.vendor_name,
        contract_type=payload.contract_type,
        description=payload.description,
        created_by=uuid.UUID(settings.DEMO_ANALYST_ID),
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)

    # Log to Audit Trail
    audit = AuditLog(
        user_id=uuid.UUID(settings.DEMO_ANALYST_ID),
        action=AuditAction.DOCUMENT_UPLOADED,
        entity_type="contract",
        entity_id=contract.id,
        details={"title": contract.title, "vendor": contract.vendor_name},
    )
    db.add(audit)
    await db.commit()

    return contract


@router.get("", response_model=List[ContractResponse])
async def list_contracts(db: AsyncSession = Depends(get_db)):
    """Lists all contracts with their versions."""
    query = select(Contract).options(selectinload(Contract.versions)).order_by(Contract.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(contract_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieves a single contract by ID with all versions."""
    query = (
        select(Contract)
        .options(selectinload(Contract.versions))
        .where(Contract.id == contract_id)
    )
    result = await db.execute(query)
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.post("/{contract_id}/versions/upload", response_model=VersionResponse)
async def upload_contract_version(
    contract_id: uuid.UUID,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Uploads a new immutable contract version (PDF):
    1. Computes SHA-256 fingerprint in memory.
    2. Saves PDF file to storage.
    3. Increments version number (v1, v2).
    4. Extracts clauses page-by-page.
    5. Evaluates compliance requirements.
    6. Appends to audit log.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # 1. Verify contract exists
    contract = await db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # 2. Stream file and compute SHA-256 checksum
    hasher = hashlib.sha256()
    file_bytes = await file.read()
    hasher.update(file_bytes)
    sha256_checksum = hasher.hexdigest()
    file_size = len(file_bytes)

    # 3. Check if exact file version already exists for this contract
    existing_ver = await db.execute(
        select(ContractVersion).where(
            ContractVersion.contract_id == contract_id,
            ContractVersion.sha256_checksum == sha256_checksum,
        )
    )
    if existing_ver.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="This exact document version (matching SHA-256) is already uploaded for this contract.",
        )

    # 4. Determine next version number
    count_res = await db.execute(
        select(func.count(ContractVersion.id)).where(ContractVersion.contract_id == contract_id)
    )
    next_version_num = (count_res.scalar() or 0) + 1

    # 5. Save file to disk
    storage_dir = settings.ensure_storage_dir()
    saved_file_name = f"{contract_id}_v{next_version_num}_{sha256_checksum[:8]}.pdf"
    file_path = storage_dir / saved_file_name
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # 6. Create immutable ContractVersion
    version = ContractVersion(
        contract_id=contract_id,
        version_number=next_version_num,
        sha256_checksum=sha256_checksum,
        file_name=file.filename,
        file_path=str(file_path),
        file_size_bytes=file_size,
        approval_status=VersionStatus.DRAFT,
        created_by=uuid.UUID(settings.DEMO_ANALYST_ID),
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)

    # 7. Extract clauses page-by-page with PyMuPDF
    clauses = await PDFExtractorService.extract_and_store_clauses(
        pdf_path=str(file_path),
        contract_version_id=version.id,
        db=db,
    )

    # 8. Run compliance requirement evaluation
    await HybridEvaluationService.evaluate_version(
        contract_version_id=version.id,
        db=db,
    )

    # 9. Record in Audit Log
    audit = AuditLog(
        user_id=uuid.UUID(settings.DEMO_ANALYST_ID),
        action=AuditAction.VERSION_CREATED,
        entity_type="contract_version",
        entity_id=version.id,
        details={
            "version_number": version.version_number,
            "sha256": sha256_checksum,
            "file_name": file.filename,
            "clauses_extracted": len(clauses),
        },
    )
    db.add(audit)
    await db.commit()

    resp = VersionResponse.model_validate(version)
    resp.clause_count = len(clauses)
    return resp


@router.get("/versions/{version_id}/clauses", response_model=List[ClauseResponse])
async def get_version_clauses(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves all segmented clauses for a specific contract version."""
    query = (
        select(Clause)
        .where(Clause.contract_version_id == version_id)
        .order_by(Clause.clause_index.asc())
    )
    res = await db.execute(query)
    return res.scalars().all()

