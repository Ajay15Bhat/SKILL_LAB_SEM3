"""
ClauseTrace Deterministic Text Diffing & Change Impact Analysis Engine.
Computes clause-by-clause additions/deletions and flags affected requirements.
"""

import difflib
import uuid
from typing import Any, Dict, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import FindingStatus
from app.schemas.diff import ClauseDiffItem, DiffResponse, ImpactedRequirement


class ContractDifferService:
    """
    Compares two contract versions deterministically using Python's difflib,
    detects modified/added/removed text, and flags requirements for reassessment.
    """

    @classmethod
    async def compute_version_diff(
        cls,
        source_version_id: uuid.UUID,
        target_version_id: uuid.UUID,
        db: AsyncSession,
    ) -> DiffResponse:
        """
        Executes clause-level diffing between v1 and v2 and identifies impacted requirements.
        """
        # 1. Fetch version metadata
        v_res = await db.execute(
            text("SELECT id, version_number, sha256_checksum FROM contract_versions WHERE id IN (:v1, :v2);"),
            {"v1": source_version_id, "v2": target_version_id},
        )
        versions = {r[0]: (r[1], r[2]) for r in v_res.fetchall()}
        
        source_ver_num, source_sha = versions.get(source_version_id, (1, "unknown"))
        target_ver_num, target_sha = versions.get(target_version_id, (2, "unknown"))

        # 2. Fetch clauses for both versions
        c_sql = text("""
            SELECT id, contract_version_id, clause_index, section_title, text_content
            FROM clauses
            WHERE contract_version_id IN (:v1, :v2)
            ORDER BY contract_version_id, clause_index ASC;
        """)
        c_res = await db.execute(c_sql, {"v1": source_version_id, "v2": target_version_id})
        
        v1_clauses: List[Dict[str, Any]] = []
        v2_clauses: List[Dict[str, Any]] = []
        for r in c_res.fetchall():
            item = {"id": r[0], "index": r[2], "section": r[3], "text": r[4]}
            if r[1] == source_version_id:
                v1_clauses.append(item)
            else:
                v2_clauses.append(item)

        # 3. Clause-by-clause comparison
        max_len = max(len(v1_clauses), len(v2_clauses))
        clause_diffs: List[ClauseDiffItem] = []
        modified_clause_ids: set[uuid.UUID] = set()

        additions = 0
        deletions = 0
        modifications = 0
        unchanged = 0

        for i in range(max_len):
            v1_c = v1_clauses[i] if i < len(v1_clauses) else None
            v2_c = v2_clauses[i] if i < len(v2_clauses) else None

            if v1_c and v2_c:
                if v1_c["text"] == v2_c["text"]:
                    unchanged += 1
                    clause_diffs.append(ClauseDiffItem(
                        clause_index=i + 1,
                        change_type="UNCHANGED",
                        section_title=v2_c["section"],
                        source_text=v1_c["text"],
                        target_text=v2_c["text"],
                        diff_lines=[],
                    ))
                else:
                    modifications += 1
                    modified_clause_ids.add(v1_c["id"])
                    
                    # Generate line-by-line diff
                    diff_lines = list(difflib.unified_diff(
                        v1_c["text"].split(". "),
                        v2_c["text"].split(". "),
                        fromfile=f"v{source_ver_num}_clause_{i+1}",
                        tofile=f"v{target_ver_num}_clause_{i+1}",
                        lineterm="",
                    ))
                    clause_diffs.append(ClauseDiffItem(
                        clause_index=i + 1,
                        change_type="MODIFIED",
                        section_title=v2_c["section"] or v1_c["section"],
                        source_text=v1_c["text"],
                        target_text=v2_c["text"],
                        diff_lines=diff_lines[2:] if len(diff_lines) > 2 else diff_lines,
                    ))

            elif not v1_c and v2_c:
                additions += 1
                clause_diffs.append(ClauseDiffItem(
                    clause_index=i + 1,
                    change_type="ADDED",
                    section_title=v2_c["section"],
                    source_text=None,
                    target_text=v2_c["text"],
                    diff_lines=[f"+ {v2_c['text']}"],
                ))

            elif v1_c and not v2_c:
                deletions += 1
                modified_clause_ids.add(v1_c["id"])
                clause_diffs.append(ClauseDiffItem(
                    clause_index=i + 1,
                    change_type="REMOVED",
                    section_title=v1_c["section"],
                    source_text=v1_c["text"],
                    target_text=None,
                    diff_lines=[f"- {v1_c['text']}"],
                ))

        # 4. Change Impact Analysis: Identify requirements grounded in modified v1 clauses
        impacted_requirements: List[ImpactedRequirement] = []
        if modified_clause_ids:
            impact_sql = text("""
                SELECT 
                    f.requirement_id,
                    r.title,
                    r.category,
                    f.evidence_clause_id
                FROM findings f
                JOIN requirements r ON r.id = f.requirement_id
                WHERE f.contract_version_id = :v1_id
                  AND f.evidence_clause_id = ANY(:clause_ids);
            """)
            imp_res = await db.execute(
                impact_sql,
                {"v1_id": source_version_id, "clause_ids": list(modified_clause_ids)},
            )
            
            for row in imp_res.fetchall():
                req_id, title, category, cl_id = row[0], row[1], row[2], row[3]
                impacted_requirements.append(ImpactedRequirement(
                    requirement_id=req_id,
                    title=title,
                    category=category,
                    impact_reason=f"Clause anchoring this requirement was modified or removed in v{target_ver_num}.",
                    flagged_status="NEEDS_REVIEW",
                ))

                # Flag the finding in v2 as NEEDS_REVIEW
                flag_sql = text("""
                    UPDATE findings
                    SET status = 'NEEDS_REVIEW',
                        analysis_notes = 'Automatically flagged: Governing clause was modified in this revision.'
                    WHERE contract_version_id = :v2_id
                      AND requirement_id = :req_id;
                """)
                await db.execute(flag_sql, {"v2_id": target_version_id, "req_id": req_id})

        return DiffResponse(
            source_version_number=source_ver_num,
            target_version_number=target_ver_num,
            source_sha256=source_sha,
            target_sha256=target_sha,
            metrics={
                "additions": additions,
                "deletions": deletions,
                "modifications": modifications,
                "unchanged": unchanged,
            },
            clause_diffs=clause_diffs,
            impacted_requirements=impacted_requirements,
        )

