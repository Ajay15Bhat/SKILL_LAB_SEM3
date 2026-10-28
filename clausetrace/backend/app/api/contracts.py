"""
Contract & Version Management API Endpoints.
Handles PDF file uploads, SHA-256 fingerprinting, and version tracking.
"""

import hashlib
import os
from pathlib import Path
import uuid
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.user_helper import ensure_demo_users
from app.models.audit import AuditLog
from app.models.base import AuditAction, VersionStatus
from app.models.contract import Clause, Contract, ContractVersion
from app.models.requirement import Requirement
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
    await ensure_demo_users(db)
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

    # Re-fetch with eager loaded relationships to avoid MissingGreenlet
    res = await db.execute(
        select(Contract)
        .options(selectinload(Contract.versions).selectinload(ContractVersion.clauses))
        .where(Contract.id == contract.id)
    )
    return res.scalar_one()


@router.get("", response_model=List[ContractResponse])
async def list_contracts(db: AsyncSession = Depends(get_db)):
    """Lists all contracts with their versions."""
    query = (
        select(Contract)
        .options(selectinload(Contract.versions).selectinload(ContractVersion.clauses))
        .order_by(Contract.created_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(contract_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieves a single contract by ID with all versions."""
    query = (
        select(Contract)
        .options(selectinload(Contract.versions).selectinload(ContractVersion.clauses))
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
    await ensure_demo_users(db)
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


@router.post("/seed-demo", tags=["Contracts & Versions"])
async def seed_demo_contract(db: AsyncSession = Depends(get_db)):
    """Seeds the demonstration CloudScale MSA with sample v1 and v2 agreements."""
    await ensure_demo_users(db)

    # 1. Ensure sample requirement exists
    req_query = select(Requirement).where(Requirement.title.ilike("%Termination%"))
    existing_req = (await db.execute(req_query)).scalar_one_or_none()
    if not existing_req:
        demo_req = Requirement(
            title="Termination for Convenience (30-Day Notice)",
            category="Termination",
            description="Contract must provide at least thirty (30) days prior written notice for termination without cause.",
            search_keywords=["terminate", "notice", "days", "written"],
            is_mandatory=True,
            created_by=uuid.UUID(settings.DEMO_ANALYST_ID),
        )
        db.add(demo_req)
        await db.commit()

    # 2. Check if demo contract exists
    contract_query = select(Contract).where(Contract.title == "Cloud Services MSA (Demo)")
    contract = (await db.execute(contract_query)).scalar_one_or_none()
    if not contract:
        contract = Contract(
            title="Cloud Services MSA (Demo)",
            vendor_name="CloudScale Corp",
            contract_type="MSA",
            description="Enterprise cloud hosting and automated backup agreement",
            created_by=uuid.UUID(settings.DEMO_ANALYST_ID),
        )
        db.add(contract)
        await db.commit()
        await db.refresh(contract)

    # 3. Locate sample PDF files
    base_dir = Path(__file__).parent.parent.parent
    sample_dir = base_dir / "sample_contracts"
    v1_pdf = sample_dir / "v1_vendor_agreement.pdf"
    v2_pdf = sample_dir / "v2_vendor_agreement.pdf"

    if not v1_pdf.exists() or not v2_pdf.exists():
        try:
            import sys
            sys.path.insert(0, str(base_dir))
            from create_sample_contracts import generate_all_samples
            generate_all_samples()
        except Exception as e:
            print("Notice: could not auto-generate contracts:", e)

    storage_dir = settings.ensure_storage_dir()

    # Upload v1 if not present
    v1_exists = (await db.execute(
        select(ContractVersion).where(
            ContractVersion.contract_id == contract.id,
            ContractVersion.version_number == 1,
        )
    )).scalar_one_or_none()

    if not v1_exists and v1_pdf.exists():
        with open(v1_pdf, "rb") as f:
            v1_bytes = f.read()
        v1_hash = hashlib.sha256(v1_bytes).hexdigest()
        v1_path = storage_dir / f"{contract.id}_v1_{v1_hash[:8]}.pdf"
        with open(v1_path, "wb") as f:
            f.write(v1_bytes)

        v1_ver = ContractVersion(
            contract_id=contract.id,
            version_number=1,
            sha256_checksum=v1_hash,
            file_name="v1_vendor_agreement.pdf",
            file_path=str(v1_path),
            file_size_bytes=len(v1_bytes),
            approval_status=VersionStatus.APPROVED,
            approved_by=uuid.UUID(settings.DEMO_REVIEWER_ID),
            created_by=uuid.UUID(settings.DEMO_ANALYST_ID),
        )
        db.add(v1_ver)
        await db.commit()
        await db.refresh(v1_ver)

        await PDFExtractorService.extract_and_store_clauses(
            pdf_path=str(v1_path),
            contract_version_id=v1_ver.id,
            db=db,
        )
        await HybridEvaluationService.evaluate_version(
            contract_version_id=v1_ver.id,
            db=db,
        )

    # Upload v2 if not present
    v2_exists = (await db.execute(
        select(ContractVersion).where(
            ContractVersion.contract_id == contract.id,
            ContractVersion.version_number == 2,
        )
    )).scalar_one_or_none()

    if not v2_exists and v2_pdf.exists():
        with open(v2_pdf, "rb") as f:
            v2_bytes = f.read()
        v2_hash = hashlib.sha256(v2_bytes).hexdigest()
        v2_path = storage_dir / f"{contract.id}_v2_{v2_hash[:8]}.pdf"
        with open(v2_path, "wb") as f:
            f.write(v2_bytes)

        v2_ver = ContractVersion(
            contract_id=contract.id,
            version_number=2,
            sha256_checksum=v2_hash,
            file_name="v2_vendor_agreement.pdf",
            file_path=str(v2_path),
            file_size_bytes=len(v2_bytes),
            approval_status=VersionStatus.DRAFT,
            created_by=uuid.UUID(settings.DEMO_ANALYST_ID),
        )
        db.add(v2_ver)
        await db.commit()
        await db.refresh(v2_ver)

        await PDFExtractorService.extract_and_store_clauses(
            pdf_path=str(v2_path),
            contract_version_id=v2_ver.id,
            db=db,
        )
        await HybridEvaluationService.evaluate_version(
            contract_version_id=v2_ver.id,
            db=db,
        )

    return {"status": "success", "contract_id": str(contract.id), "message": "Demo sample contracts loaded successfully."}


