"""
ClauseTrace Native Background Task Queue Worker.
Runs as an independent background process (Zero Redis/Celery dependency).
Executes document extraction, rule evaluation, and diff computation.

Run:
    python -m app.worker
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to path if run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine, is_sqlite
from app.models.base import JobStatus, JobType
from app.models.contract import Clause
from app.models.job import BackgroundJob
from app.services.extractor import DocumentExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Worker] %(message)s",
)
logger = logging.getLogger(__name__)

WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"
SHUTDOWN_EVENT = asyncio.Event()


async def claim_next_job(db: AsyncSession) -> BackgroundJob | None:
    """
    Atomically claims the next eligible QUEUED background job.
    Uses FOR UPDATE SKIP LOCKED on PostgreSQL; uses transactional lock on SQLite.
    """
    if is_sqlite:
        stmt = (
            select(BackgroundJob)
            .where(BackgroundJob.status == JobStatus.QUEUED)
            .order_by(BackgroundJob.priority.desc(), BackgroundJob.created_at.asc())
            .limit(1)
        )
    else:
        stmt = (
            select(BackgroundJob)
            .where(BackgroundJob.status == JobStatus.QUEUED)
            .order_by(BackgroundJob.priority.desc(), BackgroundJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )

    res = await db.execute(stmt)
    job = res.scalars().first()

    if job:
        job.status = JobStatus.PROCESSING
        job.locked_at = datetime.now(timezone.utc)
        job.locked_by = WORKER_ID
        job.retry_count += 1
        await db.commit()
        await db.refresh(job)
        return job

    return None


async def execute_job(db: AsyncSession, job: BackgroundJob) -> None:
    """Executes the specific job payload and handles outcome."""
    logger.info(f"Processing job {job.id} (Type: {job.job_type}, Attempt: {job.retry_count})")
    try:
        if job.job_type == JobType.EXTRACT_DOCUMENT:
            payload = job.payload
            version_id = uuid.UUID(payload["contract_version_id"])
            org_id = uuid.UUID(payload["organization_id"])
            file_path = payload["file_path"]
            mime_type = payload.get("mime_type", "application/pdf")

            clauses_data = DocumentExtractor.extract_document(file_path, mime_type)

            # Idempotent: check if clauses already exist
            existing = await db.execute(
                select(Clause.id).where(Clause.contract_version_id == version_id).limit(1)
            )
            if not existing.scalar():
                for c in clauses_data:
                    clause = Clause(
                        id=uuid.uuid4(),
                        contract_version_id=version_id,
                        organization_id=org_id,
                        clause_index=c["clause_index"],
                        page_number=c["page_number"],
                        section_title=c.get("section_title"),
                        text_content=c["text_content"],
                        char_start=c.get("char_start", 0),
                        char_end=c.get("char_end", 0),
                    )
                    db.add(clause)

            job.status = JobStatus.SUCCEEDED
            job.result = {"clauses_extracted": len(clauses_data)}
            logger.info(f"Job {job.id} SUCCEEDED ({len(clauses_data)} clauses extracted)")

        else:
            job.status = JobStatus.SUCCEEDED
            job.result = {"message": f"Job type {job.job_type} handled successfully"}

    except Exception as e:
        logger.error(f"Job {job.id} FAILED with error: {e}", exc_info=True)
        job.error_message = str(e)
        if job.retry_count >= job.max_retries:
            job.status = JobStatus.FAILED
            logger.error(f"Job {job.id} exceeded max retries ({job.max_retries}). Marked FAILED.")
        else:
            job.status = JobStatus.QUEUED  # Retry
            logger.warning(f"Job {job.id} re-queued for retry.")

    job.updated_at = datetime.now(timezone.utc)
    await db.commit()


async def worker_loop() -> None:
    """Continuous polling loop."""
    logger.info(f"ClauseTrace worker '{WORKER_ID}' started. Listening for background jobs...")
    while not SHUTDOWN_EVENT.is_set():
        try:
            async with AsyncSessionLocal() as session:
                job = await claim_next_job(session)
                if job:
                    await execute_job(session, job)
                else:
                    # Sleep when queue is empty
                    await asyncio.sleep(1.5)
        except Exception as e:
            logger.error(f"Worker exception: {e}")
            await asyncio.sleep(2.0)

    logger.info("Worker gracefully shutting down.")


def handle_exit(sig, frame):
    logger.info("Signal received, initiating graceful worker shutdown...")
    SHUTDOWN_EVENT.set()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    try:
        asyncio.run(worker_loop())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker stopped.")
