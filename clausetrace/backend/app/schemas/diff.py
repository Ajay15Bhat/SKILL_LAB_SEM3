"""
Pydantic Schemas for Text Diffing and Change Impact Analysis.
"""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ClauseDiffItem(BaseModel):
    clause_index: int
    change_type: str  # "UNCHANGED", "MODIFIED", "ADDED", "REMOVED"
    section_title: Optional[str] = None
    source_text: Optional[str] = None
    target_text: Optional[str] = None
    diff_lines: List[str] = []  # Line-by-line diff with +/- markers


class ImpactedRequirement(BaseModel):
    requirement_id: uuid.UUID
    title: str
    category: str
    impact_reason: str
    flagged_status: str = "NEEDS_REVIEW"


class DiffResponse(BaseModel):
    source_version_number: int
    target_version_number: int
    source_sha256: str
    target_sha256: str
    metrics: Dict[str, int]  # additions, deletions, modifications, unchanged
    clause_diffs: List[ClauseDiffItem]
    impacted_requirements: List[ImpactedRequirement]

