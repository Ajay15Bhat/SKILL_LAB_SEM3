"""
Pydantic Schemas for Requirements and Evidence-Grounded Findings.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class RequirementCreate(BaseModel):
    title: str
    category: str = "General"
    description: str
    search_keywords: List[str] = []
    is_mandatory: bool = True


class RequirementResponse(BaseModel):
    id: uuid.UUID
    title: str
    category: str
    description: str
    search_keywords: List[str]
    is_mandatory: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FindingResponse(BaseModel):
    id: uuid.UUID
    requirement_id: uuid.UUID
    requirement_title: Optional[str] = None
    contract_version_id: uuid.UUID
    status: str
    evidence_clause_id: Optional[uuid.UUID] = None
    clause_page: Optional[int] = None
    evidence_quote: Optional[str] = None
    confidence_score: Optional[float] = None
    analysis_notes: Optional[str] = None
    review_status: str
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FindingOverrideRequest(BaseModel):
    status: str  # SATISFIED, PARTIALLY_SATISFIED, NOT_SATISFIED, NEEDS_REVIEW
    analysis_notes: Optional[str] = None

