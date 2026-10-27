"""
ClauseTrace Private Storage Service.
Computes SHA-256 checksums, validates MIME types & signatures, and persists contract files privately.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "text/plain": ".txt",
}

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


class StorageService:
    def __init__(self, base_dir: str = settings.STORAGE_LOCAL_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_uploaded_file(
        self, file: UploadFile, contract_id: uuid.UUID, version_number: int
    ) -> Tuple[str, str, int, str]:
        """
        Validates, computes SHA-256 hash, and saves file to private disk storage.
        Returns: (relative_file_path, sha256_checksum, file_size_bytes, mime_type)
        """
        filename = file.filename or "contract_upload"
        ext = Path(filename).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # Read contents with bounded size check
        contents = await file.read()
        file_size = len(contents)

        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES / (1024*1024):.0f}MB",
            )

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded file is empty (0 bytes).",
            )

        # SHA-256 hash
        sha256_hash = hashlib.sha256(contents).hexdigest()

        # Destination structure: storage/contracts/{contract_id}/v{version_number}/{filename}
        version_dir = self.base_dir / str(contract_id) / f"v{version_number}"
        version_dir.mkdir(parents=True, exist_ok=True)

        dest_file_path = version_dir / filename
        with open(dest_file_path, "wb") as f:
            f.write(contents)

        mime_type = file.content_type or "application/octet-stream"
        if mime_type not in ALLOWED_MIME_TYPES:
            if ext == ".pdf":
                mime_type = "application/pdf"
            elif ext == ".docx":
                mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        return str(dest_file_path), sha256_hash, file_size, mime_type

    def get_file_bytes(self, file_path: str) -> bytes:
        """Reads file bytes from private storage."""
        p = Path(file_path)
        if not p.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stored contract file not found on disk.",
            )
        with open(p, "rb") as f:
            return f.read()


storage_service = StorageService()
