"""
ClauseTrace Contracts and Versions Management API Endpoints.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.audit import AuditLog
from app.models.auth import User
from app.models.base import (
    AuditAction,
    JobStatus,
    JobType,
    UserRole,
    VersionStatus,
)
from app.models.contract import Clause, Contract, ContractVersion
from app.models.diff import VersionDiff
from app.models.job import BackgroundJob
from app.models.requirement import Finding
from app.schemas import (
    AuditLogRead,
    CompareRequest,
    ContractCreate,
    ContractDetail,
    ContractRead,
    VersionDiffRead,
    VersionRead,
)
from app.services.audit_service import audit_service
from app.services.diff_engine import diff_engine
from app.services.extractor import DocumentExtractor
from app.services.storage import storage_service

router = APIRouter(prefix="/contracts", tags=["Contracts & Versions"])


@router.post("", response_model=ContractRead, status_code=status.HTTP_201_CREATED)
async def create_contract(
    req: ContractCreate,
    current_user: User = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new enterprise vendor agreement container."""
    contract = Contract(
        id=uuid.uuid4(),
        organization_id=current_user.organization_id,
        title=req.title,
        vendor_name=req.vendor_name,
        contract_type=req.contract_type,
        description=req.description,
        created_by=current_user.id,
    )
    db.add(contract)
    await db.flush()

    await audit_service.log_event(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.DOCUMENT_UPLOADED,
        entity_type="CONTRACT",
        entity_id=contract.id,
        metadata_after={"title": contract.title, "vendor": contract.vendor_name},
    )
    await db.commit()
    await db.refresh(contract)
    return contract


@router.get("", response_model=List[ContractRead])
async def list_contracts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists all contracts belonging to current user's organization."""
    stmt = (
        select(Contract)
        .options(selectinload(Contract.versions))
        .where(Contract.organization_id == current_user.organization_id)
        .order_by(Contract.created_at.desc())
    )
    res = await db.execute(stmt)
    contracts = res.scalars().all()

    output = []
    for c in contracts:
        c_read = ContractRead.model_validate(c)
        if c.versions:
            latest = max(c.versions, key=lambda v: v.version_number)
            c_read.latest_version = latest.version_number
            c_read.latest_version_id = latest.id
            c_read.latest_status = latest.approval_status
        output.append(c_read)
    return output


@router.get("/{contract_id}", response_model=ContractDetail)
async def get_contract(
    contract_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves a contract with all its immutable revisions."""
    stmt = (
        select(Contract)
        .options(selectinload(Contract.versions))
        .where(
            Contract.id == contract_id,
            Contract.organization_id == current_user.organization_id,
        )
    )
    res = await db.execute(stmt)
    contract = res.scalars().first()

    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found or belongs to another organization.",
        )

    versions_sorted = sorted(contract.versions, key=lambda v: v.version_number, reverse=True)
    c_read = ContractDetail.model_validate(contract)
    c_read.versions = [VersionRead.model_validate(v) for v in versions_sorted]
    if versions_sorted:
        c_read.latest_version = versions_sorted[0].version_number
        c_read.latest_version_id = versions_sorted[0].id
        c_read.latest_status = versions_sorted[0].approval_status
    return c_read


@router.post(
    "/{contract_id}/versions",
    response_model=VersionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_contract_version(
    contract_id: uuid.UUID,
    response: Response,
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Uploads a new immutable document version.
    Computes SHA-256 fingerprint, stores file privately, and schedules parsing.
    Returns HTTP 202 Accepted.
    """
    # 1. Verify contract tenancy
    stmt = select(Contract).where(
        Contract.id == contract_id,
        Contract.organization_id == current_user.organization_id,
    )
    res = await db.execute(stmt)
    contract = res.scalars().first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found in your organization.")

    # 2. Concurrency-safe version numbering
    v_stmt = select(func.coalesce(func.max(ContractVersion.version_number), 0)).where(
        ContractVersion.contract_id == contract_id
    )
    v_res = await db.execute(v_stmt)
    next_version_num = (v_res.scalar() or 0) + 1

    # 3. Store file privately & compute SHA-256
    file_path, sha256_hash, file_size, mime_type = await storage_service.save_uploaded_file(
        file=file,
        contract_id=contract_id,
        version_number=next_version_num,
    )

    # 4. Check duplicate checksum under this contract
    chk_stmt = select(ContractVersion).where(
        ContractVersion.contract_id == contract_id,
        ContractVersion.sha256_checksum == sha256_hash,
    )
    chk_res = await db.execute(chk_stmt)
    if chk_res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This exact file content already exists for this contract (SHA-256: {sha256_hash[:12]}...).",
        )

    # 5. Create Version Record (starts strictly in DRAFT)
    version = ContractVersion(
        id=uuid.uuid4(),
        contract_id=contract_id,
        organization_id=current_user.organization_id,
        version_number=next_version_num,
        sha256_checksum=sha256_hash,
        file_name=file.filename or "uploaded_contract",
        file_path=file_path,
        file_size_bytes=file_size,
        mime_type=mime_type,
        approval_status=VersionStatus.DRAFT,
        created_by=current_user.id,
    )
    db.add(version)
    await db.flush()

    # 6. Create Persistent Processing Job
    job = BackgroundJob(
        id=uuid.uuid4(),
        job_type=JobType.EXTRACT_DOCUMENT,
        payload={
            "contract_version_id": str(version.id),
            "file_path": file_path,
            "mime_type": mime_type,
            "organization_id": str(current_user.organization_id),
        },
        status=JobStatus.QUEUED,
        priority=10,
    )
    db.add(job)
    await db.flush()

    # 7. Record Audit Events
    await audit_service.log_event(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.VERSION_CREATED,
        entity_type="CONTRACT_VERSION",
        entity_id=version.id,
        metadata_after={
            "version_number": next_version_num,
            "sha256": sha256_hash,
            "file_name": version.file_name,
            "job_id": str(job.id),
        },
    )

    # Immediate extraction execution for responsive demo / tests
    try:
        extracted_clauses = DocumentExtractor.extract_document(file_path, mime_type)
        for c_data in extracted_clauses:
            clause = Clause(
                id=uuid.uuid4(),
                contract_version_id=version.id,
                organization_id=current_user.organization_id,
                clause_index=c_data["clause_index"],
                page_number=c_data["page_number"],
                section_title=c_data.get("section_title"),
                text_content=c_data["text_content"],
                char_start=c_data.get("char_start", 0),
                char_end=c_data.get("char_end", 0),
            )
            db.add(clause)

        job.status = JobStatus.SUCCEEDED
        job.result = {"clauses_extracted": len(extracted_clauses)}
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_message = str(e)

    await db.commit()
    await db.refresh(version)

    response.headers["X-Job-Id"] = str(job.id)
    return version


@router.get("/{contract_id}/versions", response_model=List[VersionRead])
async def list_contract_versions(
    contract_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists all versions of a contract in descending version order."""
    stmt = (
        select(ContractVersion)
        .where(
            ContractVersion.contract_id == contract_id,
            ContractVersion.organization_id == current_user.organization_id,
        )
        .order_by(ContractVersion.version_number.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/{contract_id}/compare", response_model=VersionDiffRead)
async def compare_contract_versions(
    contract_id: uuid.UUID,
    req: CompareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compares two explicit versions of a contract.
    Detects added, removed, and modified clauses, computes diffs, and flags impacted requirements.
    """
    # Fetch source and target versions
    s_stmt = select(ContractVersion).where(
        ContractVersion.id == req.source_version_id,
        ContractVersion.contract_id == contract_id,
        ContractVersion.organization_id == current_user.organization_id,
    )
    t_stmt = select(ContractVersion).where(
        ContractVersion.id == req.target_version_id,
        ContractVersion.contract_id == contract_id,
        ContractVersion.organization_id == current_user.organization_id,
    )
    s_res = await db.execute(s_stmt)
    t_res = await db.execute(t_stmt)
    source_ver = s_res.scalars().first()
    target_ver = t_res.scalars().first()

    if not source_ver or not target_ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both contract versions not found in your organization.",
        )

    # Check if a diff was already computed between this pair
    existing_diff_stmt = select(VersionDiff).where(
        VersionDiff.source_version_id == source_ver.id,
        VersionDiff.target_version_id == target_ver.id,
    )
    existing_diff = (await db.execute(existing_diff_stmt)).scalars().first()
    if existing_diff:
        return existing_diff

    diff_record = await diff_engine.compare_versions(
        db=db,
        organization_id=current_user.organization_id,
        source_version=source_ver,
        target_version=target_ver,
    )

    await audit_service.log_event(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.DIFF_GENERATED,
        entity_type="VERSION_DIFF",
        entity_id=diff_record.id,
        metadata_after={
            "source_v": source_ver.version_number,
            "target_v": target_ver.version_number,
            "summary": diff_record.diff_summary,
        },
    )
    await db.commit()
    await db.refresh(diff_record)
    return diff_record


@router.get("/{contract_id}/audit-events", response_model=List[AuditLogRead])
async def get_contract_audit_events(
    contract_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the chronological audit trail for a contract, including all its versions and decisions.
    """
    # Verify contract ownership
    c_check = await db.execute(
        select(Contract.id).where(
            Contract.id == contract_id,
            Contract.organization_id == current_user.organization_id,
        )
    )
    if not c_check.scalar():
        raise HTTPException(status_code=404, detail="Contract not found in your organization.")

    # Get all version IDs for this contract
    v_stmt = select(ContractVersion.id).where(ContractVersion.contract_id == contract_id)
    v_res = await db.execute(v_stmt)
    version_ids = list(v_res.scalars().all())

    # Get finding IDs and diff IDs for this contract
    finding_ids = []
    diff_ids = []
    if version_ids:
        f_stmt = select(Finding.id).where(Finding.contract_version_id.in_(version_ids))
        finding_ids = list((await db.execute(f_stmt)).scalars().all())

        d_stmt = select(VersionDiff.id).where(
            (VersionDiff.source_version_id.in_(version_ids)) | (VersionDiff.target_version_id.in_(version_ids))
        )
        diff_ids = list((await db.execute(d_stmt)).scalars().all())

    all_entity_ids = [contract_id] + version_ids + finding_ids + diff_ids

    stmt = (
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .where(
            AuditLog.organization_id == current_user.organization_id,
            AuditLog.entity_id.in_(all_entity_ids),
        )
        .order_by(AuditLog.created_at.desc())
    )
    res = await db.execute(stmt)
    logs = res.scalars().all()

    output = []
    for l in logs:
        read_obj = AuditLogRead.model_validate(l)
        if l.user:
            read_obj.actor_email = l.user.email
        output.append(read_obj)
    return output
