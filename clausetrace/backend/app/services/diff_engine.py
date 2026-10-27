"""
ClauseTrace Deterministic Version Diff and Change Impact Engine.
Aligns clauses, identifies added/removed/modified passages, generates word-level diffs,
and flags requirements whose underlying evidence clauses were altered.
"""

from __future__ import annotations

import difflib
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Clause, ContractVersion
from app.models.diff import VersionDiff
from app.models.requirement import Finding, Requirement


class DiffEngine:
    @staticmethod
    async def compare_versions(
        db: AsyncSession,
        organization_id: uuid.UUID,
        source_version: ContractVersion,
        target_version: ContractVersion,
    ) -> VersionDiff:
        """
        Generates a comprehensive change-impact diff between source and target versions.
        """
        # 1. Checksum comparison
        if source_version.sha256_checksum == target_version.sha256_checksum:
            payload = {
                "identical": True,
                "added_clauses": [],
                "removed_clauses": [],
                "modified_clauses": [],
                "flagged_requirement_ids": [],
                "metrics": {"additions": 0, "deletions": 0, "modifications": 0},
            }
            summary = f"Versions v{source_version.version_number} and v{target_version.version_number} are bit-for-bit identical (SHA-256 match)."
            diff_record = VersionDiff(
                id=uuid.uuid4(),
                organization_id=organization_id,
                source_version_id=source_version.id,
                target_version_id=target_version.id,
                diff_summary=summary,
                diff_payload=payload,
            )
            db.add(diff_record)
            await db.flush()
            return diff_record

        # 2. Fetch all clauses for both versions
        s_stmt = (
            select(Clause)
            .where(Clause.contract_version_id == source_version.id)
            .order_by(Clause.clause_index.asc())
        )
        t_stmt = (
            select(Clause)
            .where(Clause.contract_version_id == target_version.id)
            .order_by(Clause.clause_index.asc())
        )
        s_res = await db.execute(s_stmt)
        t_res = await db.execute(t_stmt)
        source_clauses = list(s_res.scalars().all())
        target_clauses = list(t_res.scalars().all())

        # 3. Match clauses
        modified_clauses = []
        added_clauses = []
        removed_clauses = []
        modified_source_clause_ids = set()

        max_len = max(len(source_clauses), len(target_clauses))
        for i in range(max_len):
            s_clause = source_clauses[i] if i < len(source_clauses) else None
            t_clause = target_clauses[i] if i < len(target_clauses) else None

            if s_clause and t_clause:
                s_text = s_clause.text_content.strip()
                t_text = t_clause.text_content.strip()

                if s_text != t_text:
                    # Clause was modified
                    modified_source_clause_ids.add(s_clause.id)
                    word_diffs = DiffEngine._compute_word_diff(s_text, t_text)
                    modified_clauses.append(
                        {
                            "source_clause_id": str(s_clause.id),
                            "target_clause_id": str(t_clause.id),
                            "clause_index": t_clause.clause_index,
                            "page_number": t_clause.page_number,
                            "section_title": t_clause.section_title or s_clause.section_title or f"Clause {t_clause.clause_index}",
                            "source_text": s_text,
                            "target_text": t_text,
                            "diff_tokens": word_diffs,
                        }
                    )
            elif t_clause and not s_clause:
                added_clauses.append(
                    {
                        "target_clause_id": str(t_clause.id),
                        "clause_index": t_clause.clause_index,
                        "page_number": t_clause.page_number,
                        "section_title": t_clause.section_title,
                        "target_text": t_clause.text_content,
                    }
                )
            elif s_clause and not t_clause:
                modified_source_clause_ids.add(s_clause.id)
                removed_clauses.append(
                    {
                        "source_clause_id": str(s_clause.id),
                        "clause_index": s_clause.clause_index,
                        "page_number": s_clause.page_number,
                        "section_title": s_clause.section_title,
                        "source_text": s_clause.text_content,
                    }
                )

        # 4. Change Impact: Identify requirements whose evidence clauses were changed
        flagged_requirement_ids = []
        flagged_requirement_details = []

        if modified_source_clause_ids:
            # Query findings from source version linked to modified clauses
            f_stmt = (
                select(Finding, Requirement)
                .join(Requirement, Finding.requirement_id == Requirement.id)
                .where(
                    Finding.contract_version_id == source_version.id,
                    Finding.evidence_clause_id.in_(list(modified_source_clause_ids)),
                )
            )
            f_res = await db.execute(f_stmt)
            for finding, req in f_res.all():
                flagged_requirement_ids.append(str(req.id))
                flagged_requirement_details.append(
                    {
                        "requirement_id": str(req.id),
                        "title": req.title,
                        "category": req.category,
                        "previous_status": str(finding.status.value if hasattr(finding.status, "value") else finding.status),
                        "reason": "Supporting clause text was altered between versions.",
                    }
                )

        summary = (
            f"Compared v{source_version.version_number} against v{target_version.version_number}: "
            f"{len(modified_clauses)} modified clauses, {len(added_clauses)} added, "
            f"{len(removed_clauses)} removed. {len(flagged_requirement_ids)} requirements flagged for re-review."
        )

        payload = {
            "identical": False,
            "modified_clauses": modified_clauses,
            "added_clauses": added_clauses,
            "removed_clauses": removed_clauses,
            "flagged_requirement_ids": flagged_requirement_ids,
            "flagged_requirements": flagged_requirement_details,
            "metrics": {
                "modifications": len(modified_clauses),
                "additions": len(added_clauses),
                "deletions": len(removed_clauses),
                "flagged_requirements_count": len(flagged_requirement_ids),
            },
        }

        diff_record = VersionDiff(
            id=uuid.uuid4(),
            organization_id=organization_id,
            source_version_id=source_version.id,
            target_version_id=target_version.id,
            diff_summary=summary,
            diff_payload=payload,
        )
        db.add(diff_record)
        await db.flush()

        return diff_record

    @staticmethod
    def _compute_word_diff(old_text: str, new_text: str) -> List[Dict[str, str]]:
        """
        Produces granular word-level diff tokens:
        [{"type": "equal", "text": "..."}, {"type": "delete", "text": "30 days'"}, {"type": "insert", "text": "60 days'"}]
        """
        old_words = old_text.split()
        new_words = new_text.split()

        matcher = difflib.SequenceMatcher(None, old_words, new_words)
        tokens = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                tokens.append({"type": "equal", "text": " ".join(old_words[i1:i2])})
            elif tag == "replace":
                tokens.append({"type": "delete", "text": " ".join(old_words[i1:i2])})
                tokens.append({"type": "insert", "text": " ".join(new_words[j1:j2])})
            elif tag == "delete":
                tokens.append({"type": "delete", "text": " ".join(old_words[i1:i2])})
            elif tag == "insert":
                tokens.append({"type": "insert", "text": " ".join(new_words[j1:j2])})

        return tokens


diff_engine = DiffEngine()
