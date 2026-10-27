"""
Pydantic Schemas for Version Approvals and Digital Signatures.
"""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ApprovalRequest(BaseModel):
    decision: str = "APPROVED"  # "APPROVED" or "REJECTED"
    comments: Optional[str] = None


class ApprovalResponse(BaseModel):
    version_id: uuid.UUID
    version_number: int
    approval_status: str
    approved_by: uuid.UUID
    approved_at: datetime
    signature_hash: str
    comments: Optional[str] = None

