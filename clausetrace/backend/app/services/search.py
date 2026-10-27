"""
ClauseTrace Deterministic Passage Retrieval and Ranking Service.
Transparent scoring method based on keyword frequency, title relevance, and phrase matches.
"""

from __future__ import annotations

import re
import uuid
from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Clause


class SearchService:
    @staticmethod
    async def search_clauses(
        db: AsyncSession,
        contract_version_id: uuid.UUID,
        keywords: List[str],
        query_text: str = "",
        limit: int = 5,
    ) -> List[Tuple[Clause, float]]:
        """
        Retrieves candidate clauses for a requirement.
        Returns a sorted list of (Clause, score) tuples.
        """
        stmt = (
            select(Clause)
            .where(Clause.contract_version_id == contract_version_id)
            .order_by(Clause.clause_index.asc())
        )
        res = await db.execute(stmt)
        clauses = res.scalars().all()

        if not clauses:
            return []

        # Build list of search tokens
        tokens = set()
        for kw in keywords:
            tokens.update(re.findall(r"\w+", kw.lower()))
        if query_text:
            tokens.update(re.findall(r"\w+", query_text.lower()))

        # Remove generic stopwords
        stopwords = {"the", "and", "or", "to", "of", "in", "for", "a", "an", "is", "be", "with"}
        clean_tokens = [t for t in tokens if t not in stopwords and len(t) > 2]

        scored_clauses: List[Tuple[Clause, float]] = []

        for clause in clauses:
            content_lower = clause.text_content.lower()
            title_lower = (clause.section_title or "").lower()

            score = 0.0

            # Match exact phrases from keywords
            for kw in keywords:
                if len(kw) > 3 and kw.lower() in content_lower:
                    score += 3.0
                if len(kw) > 3 and kw.lower() in title_lower:
                    score += 4.0

            # Match individual tokens
            for token in clean_tokens:
                matches_content = len(re.findall(r"\b" + re.escape(token) + r"\b", content_lower))
                matches_title = len(re.findall(r"\b" + re.escape(token) + r"\b", title_lower))
                score += (matches_content * 1.0) + (matches_title * 2.5)

            if score > 0:
                scored_clauses.append((clause, score))

        # Sort descending by score
        scored_clauses.sort(key=lambda x: x[1], reverse=True)
        return scored_clauses[:limit]


search_service = SearchService()
