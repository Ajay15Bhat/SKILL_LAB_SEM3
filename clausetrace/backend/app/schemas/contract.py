"""
Pydantic Schemas for Contracts, Immutable Versions, and Clauses.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ClauseResponse(BaseModel):
    id: uuid.UUID
    clause_index: int
    page_number: int
    section_title: Optional[str] = None
    text_content: str
    char_start: int
    char_end: int

    model_config = ConfigDict(from_attributes=True)


class VersionResponse(BaseModel):
    id: uuid.UUID
    contract_id: uuid.UUID
    version_number: int
    sha256_checksum: str
    file_name: str
    file_size_bytes: int
    approval_status: str
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    clause_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class ContractCreate(BaseModel):
    title: str
    vendor_name: str
    contract_type: str = "MSA"
    description: Optional[str] = None


class ContractResponse(BaseModel):
    id: uuid.UUID
    title: str
    vendor_name: str
    contract_type: str
    description: Optional[str] = None
    created_at: datetime
    versions: List[VersionResponse] = []

    model_config = ConfigDict(from_attributes=True)

