"""
ClauseTrace Evidence-Grounded Requirement Evaluation Engine.
Provides deterministic baseline rule evaluation with evidence provenance.
Supports optional Gemini enrichment when configured.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Dict, Optional, Tuple

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.base import FindingStatus, ReviewStatus
from app.models.contract import Clause
from app.models.requirement import Finding, Requirement
from app.services.search import search_service

logger = logging.getLogger(__name__)

WORD_TO_NUM = {
    "ten": 10,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "forty-five": 45,
    "forty five": 45,
    "sixty": 60,
    "ninety": 90,
    "120": 120,
    "one hundred twenty": 120,
}


class RequirementEvaluator:
    @staticmethod
    async def evaluate_requirement(
        db: AsyncSession,
        requirement: Requirement,
        contract_version_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Finding:
        """
        Evaluates a requirement against contract clauses.
        Produces an evidence-grounded finding with exact clause reference and citation.
        """
        candidates = await search_service.search_clauses(
            db=db,
            contract_version_id=contract_version_id,
            keywords=requirement.search_keywords,
            query_text=f"{requirement.title} {requirement.description}",
            limit=3,
        )

        if not candidates:
            return Finding(
                id=uuid.uuid4(),
                organization_id=organization_id,
                requirement_id=requirement.id,
                contract_version_id=contract_version_id,
                status=FindingStatus.NOT_FOUND,
                evidence_clause_id=None,
                evidence_quote=None,
                confidence_score=0.90,
                analysis_notes=f"No relevant contractual passage found matching keywords: {', '.join(requirement.search_keywords)}.",
                suggested_by="DETERMINISTIC_SEARCH",
                review_status=ReviewStatus.PROPOSED,
            )

        best_clause, relevance_score = candidates[0]
        text = best_clause.text_content
        text_lower = text.lower()

        status, quote, notes, confidence = RequirementEvaluator._apply_domain_rules(
            requirement, best_clause, text, text_lower
        )

        # Optional Gemini Enrichment if configured
        if settings.GEMINI_API_KEY and "YOUR_GEMINI" not in settings.GEMINI_API_KEY:
            try:
                gemini_status, gemini_notes = await RequirementEvaluator._call_gemini(
                    requirement, best_clause.text_content
                )
                if gemini_notes:
                    notes += f" [Gemini AI Analysis: {gemini_notes}]"
            except Exception as e:
                logger.warning(f"Optional Gemini enrichment skipped: {e}")

        return Finding(
            id=uuid.uuid4(),
            organization_id=organization_id,
            requirement_id=requirement.id,
            contract_version_id=contract_version_id,
            status=status,
            evidence_clause_id=best_clause.id,
            evidence_quote=quote,
            confidence_score=confidence,
            analysis_notes=notes,
            suggested_by="DETERMINISTIC_RULE_ENGINE",
            review_status=ReviewStatus.PROPOSED,
        )

    @staticmethod
    def _apply_domain_rules(
        requirement: Requirement, clause: Clause, text: str, text_lower: str
    ) -> Tuple[FindingStatus, str, str, float]:
        """Deterministic evaluation based on clause categories and numerical thresholds."""
        cat_lower = (requirement.category or "").lower()
        title_lower = (requirement.title or "").lower()

        # 1. Termination and Notice Period Rules
        if "termination" in cat_lower or "notice" in cat_lower or "termination" in title_lower:
            # Pattern matches: "thirty (30) days", "30 days", "60 days' written notice", "notice of sixty (60) days"
            days = None
            match_start = 0

            # Match digits inside parentheses like "thirty (30) days" or plain "30 days"
            m = re.search(r"\((\d+)\)\s*(?:calendar\s+|business\s+)?days?", text_lower)
            if not m:
                m = re.search(r"\b(\d+)\s*(?:calendar\s+|business\s+)?days?", text_lower)
            if not m:
                # Word match like "thirty days" or "sixty days"
                for word, val in WORD_TO_NUM.items():
                    if f"{word} days" in text_lower or f"{word} (" in text_lower:
                        days = val
                        m = re.search(re.escape(word), text_lower)
                        break

            if m:
                if days is None and m.group(1):
                    days = int(m.group(1))
                match_start = m.start()

            if days is not None:
                sentence = RequirementEvaluator._extract_surrounding_sentence(text, match_start)
                if "30" in requirement.description or "30" in requirement.title or "not exceed 30" in requirement.description.lower():
                    if days <= 30:
                        return (
                            FindingStatus.SATISFIED,
                            sentence,
                            f"Verified termination notice period of {days} days in Section '{clause.section_title}' (Page {clause.page_number}), which complies with the maximum allowable 30 days threshold.",
                            0.95,
                        )
                    else:
                        return (
                            FindingStatus.NOT_SATISFIED,
                            sentence,
                            f"VIOLATION: Contract specifies {days} days' termination notice in Section '{clause.section_title}' (Page {clause.page_number}), which EXCEEDS the required limit of 30 days.",
                            0.95,
                        )
                else:
                    return (
                        FindingStatus.SATISFIED,
                        sentence,
                        f"Found termination notice specification of {days} days in Section '{clause.section_title}'.",
                        0.90,
                    )

        # 2. Payment Terms Rules
        if "payment" in cat_lower or "invoice" in cat_lower:
            days = None
            m = re.search(r"(?:net\s*\(?(\d+)\)?|within\s*\(?(\d+)\)?\s*days|(\d+)\s*days\s*of\s*receipt)", text_lower)
            if m:
                num_str = m.group(1) or m.group(2) or m.group(3)
                days = int(num_str)
                sentence = RequirementEvaluator._extract_surrounding_sentence(text, m.start())
                if days >= 30:
                    return (
                        FindingStatus.SATISFIED,
                        sentence,
                        f"Payment terms of {days} days identified in Section '{clause.section_title}' (Page {clause.page_number}), satisfying standard Net 30 requirements.",
                        0.92,
                    )
                else:
                    return (
                        FindingStatus.NOT_SATISFIED,
                        sentence,
                        f"Payment terms require payment within {days} days in Section '{clause.section_title}', which is less than the required Net 30 minimum.",
                        0.92,
                    )

        # 3. Confidentiality Survival Rules
        if "confidential" in cat_lower or "confidential" in title_lower:
            m = re.search(r"survive[\w\s\(\)]{1,40}?\(?(\d+)\)?\s*(?:years|year)", text_lower)
            if not m:
                for word, val in [("three", 3), ("five", 5), ("two", 2), ("one", 1)]:
                    if f"{word} ({val})" in text_lower or f"{word} years" in text_lower:
                        m = re.search(re.escape(word), text_lower)
                        years = val
                        break
            else:
                years = int(m.group(1))

            if m:
                sentence = RequirementEvaluator._extract_surrounding_sentence(text, m.start())
                if years >= 3:
                    return (
                        FindingStatus.SATISFIED,
                        sentence,
                        f"Confidentiality survival period of {years} years identified in Section '{clause.section_title}' (Page {clause.page_number}), meeting minimum 3-year survival requirement.",
                        0.92,
                    )
                else:
                    return (
                        FindingStatus.PARTIALLY_SATISFIED,
                        sentence,
                        f"Confidentiality survives for only {years} years in Section '{clause.section_title}', below the recommended 3-year threshold.",
                        0.88,
                    )

        # 4. Liability and Indemnification Rules
        if "liability" in cat_lower or "indemn" in cat_lower:
            has_indemnity = "indemnif" in text_lower or "hold harmless" in text_lower
            has_cap_exception = "gross negligence" in text_lower or "willful" in text_lower or "confidentiality" in text_lower
            sentence = text[:300] + ("..." if len(text) > 300 else "")
            if has_indemnity and has_cap_exception:
                return (
                    FindingStatus.SATISFIED,
                    sentence,
                    f"Found indemnification and liability terms with customary carve-outs in Section '{clause.section_title}' (Page {clause.page_number}).",
                    0.88,
                )
            elif has_indemnity:
                return (
                    FindingStatus.PARTIALLY_SATISFIED,
                    sentence,
                    f"Indemnification clause present in Section '{clause.section_title}', but unlimited liability carve-outs require legal confirmation.",
                    0.80,
                )

        quote = text[:250] + ("..." if len(text) > 250 else "")
        return (
            FindingStatus.NEEDS_REVIEW,
            quote,
            f"Candidate passage identified in Section '{clause.section_title}' (Page {clause.page_number}). Requires human reviewer verification against criteria.",
            0.75,
        )

    @staticmethod
    def _extract_surrounding_sentence(text: str, char_pos: int) -> str:
        """Extracts the full sentence containing the matched character position."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        running_pos = 0
        for s in sentences:
            start = running_pos
            end = running_pos + len(s)
            running_pos = end + 1
            if start <= char_pos <= end:
                return s.strip()
        return text[:200].strip()

    @staticmethod
    async def _call_gemini(requirement: Requirement, clause_text: str) -> Tuple[Optional[str], Optional[str]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
        prompt = (
            f"Requirement: {requirement.title}\n"
            f"Criteria: {requirement.description}\n\n"
            f"Contract Clause: {clause_text}\n\n"
            "Does the clause satisfy the requirement? Respond in 1-2 concise factual sentences."
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                return None, text.strip()
        return None, None


evaluator = RequirementEvaluator()
