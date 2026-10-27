"""
ClauseTrace Hybrid Retrieval & Requirement Evaluation Engine.
Combines PostgreSQL Deterministic FTS (tsvector/ts_rank_cd) with Google Gemini Flash.
"""

import json
import re
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.base import FindingStatus, ReviewStatus
from app.models.contract import Clause
from app.models.requirement import Finding, Requirement


class HybridEvaluationService:
    """
    Executes the 2-step evaluation pipeline:
    1. Deterministic Candidate Retrieval: PostgreSQL tsvector + ts_rank_cd.
    2. Semantic Legal Reasoning: Google Gemini Flash.
    """

    @classmethod
    async def find_candidate_clauses_fts(
        cls,
        contract_version_id: uuid.UUID,
        keywords: List[str],
        fallback_query: str,
        db: AsyncSession,
        limit: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the most relevant clauses using PostgreSQL Full-Text Search.
        """
        # Build search query string
        clean_terms = [re.sub(r"[^\w\s]", "", k).strip() for k in keywords if k.strip()]
        if clean_terms:
            tsquery_str = " | ".join(clean_terms)
        else:
            tsquery_str = fallback_query

        # Execute PostgreSQL tsvector ranking query
        sql = text("""
            SELECT 
                id,
                clause_index,
                page_number,
                section_title,
                text_content,
                ts_rank_cd(search_vector, plainto_tsquery('english', :query)) AS rank
            FROM clauses
            WHERE contract_version_id = :version_id
              AND (
                  search_vector @@ plainto_tsquery('english', :query)
                  OR text_content ILIKE :wildcard
              )
            ORDER BY rank DESC, clause_index ASC
            LIMIT :limit;
        """)

        first_term = clean_terms[0] if clean_terms else fallback_query.split()[0]
        result = await db.execute(
            sql,
            {
                "version_id": contract_version_id,
                "query": tsquery_str,
                "wildcard": f"%{first_term}%",
                "limit": limit,
            },
        )
        rows = result.fetchall()

        # If strict FTS found nothing, fallback to simple top clauses
        if not rows:
            fallback_sql = text("""
                SELECT id, clause_index, page_number, section_title, text_content, 0.1 AS rank
                FROM clauses
                WHERE contract_version_id = :version_id
                ORDER BY clause_index ASC
                LIMIT :limit;
            """)
            fb_res = await db.execute(fallback_sql, {"version_id": contract_version_id, "limit": limit})
            rows = fb_res.fetchall()

        candidates = []
        for r in rows:
            candidates.append({
                "id": r[0],
                "clause_index": r[1],
                "page_number": r[2],
                "section_title": r[3],
                "text_content": r[4],
                "rank": float(r[5]) if r[5] is not None else 0.0,
            })
        return candidates

    @classmethod
    async def evaluate_requirement_with_ai(
        cls,
        requirement: Requirement,
        candidate_clauses: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Evaluates candidate clauses against a requirement using Gemini Flash.
        Falls back cleanly to deterministic scores if Gemini is unavailable.
        """
        if not settings.GEMINI_API_KEY or not candidate_clauses:
            top_clause = candidate_clauses[0] if candidate_clauses else None
            return {
                "status": FindingStatus.NEEDS_REVIEW,
                "evidence_clause_id": top_clause["id"] if top_clause else None,
                "evidence_quote": top_clause["text_content"][:300] if top_clause else None,
                "confidence_score": top_clause["rank"] if top_clause else 0.5,
                "analysis_notes": "Deterministic FTS candidate retrieved. Manual review required.",
            }

        # Build prompt for Gemini
        clauses_context = "\n\n".join(
            f"[Clause {c['clause_index']} (Page {c['page_number']})]: {c['text_content']}"
            for c in candidate_clauses
        )

        prompt = f"""
You are an expert contract compliance auditor.
Evaluate whether the following contract clauses satisfy this specific requirement:

REQUIREMENT TITLE: {requirement.title}
REQUIREMENT DESCRIPTION: {requirement.description}

CANDIDATE CONTRACT CLAUSES:
{clauses_context}

Respond STRICTLY with a valid JSON object in this format (no markdown code blocks, just raw JSON):
{{
  "status": "SATISFIED" | "PARTIALLY_SATISFIED" | "NOT_SATISFIED" | "NOT_FOUND",
  "matched_clause_index": <number or null>,
  "evidence_quote": "<exact sentence or passage from the clauses that supports this>",
  "confidence_score": <float between 0.0 and 1.0>,
  "analysis_notes": "<brief 1-2 sentence explanation of whether and why the requirement is satisfied>"
}}
"""

        try:
            import asyncio
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            # Run generate_content with an 8-second hard timeout to prevent any freezing
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                ),
                timeout=8.0,
            )
            raw_text = response.text.strip()
            
            # Clean markdown code blocks if returned
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)

            ai_data = json.loads(raw_text)

            # Match evidence_clause_id by index
            matched_idx = ai_data.get("matched_clause_index")
            matched_clause_id = None
            if matched_idx is not None:
                for c in candidate_clauses:
                    if c["clause_index"] == matched_idx:
                        matched_clause_id = c["id"]
                        break
            if not matched_clause_id and candidate_clauses:
                matched_clause_id = candidate_clauses[0]["id"]

            return {
                "status": ai_data.get("status", FindingStatus.NEEDS_REVIEW),
                "evidence_clause_id": matched_clause_id,
                "evidence_quote": ai_data.get("evidence_quote"),
                "confidence_score": float(ai_data.get("confidence_score", 0.85)),
                "analysis_notes": ai_data.get("analysis_notes"),
            }

        except Exception as e:
            # Graceful fallback: Never crash the pipeline
            top_clause = candidate_clauses[0] if candidate_clauses else None
            return {
                "status": FindingStatus.NEEDS_REVIEW,
                "evidence_clause_id": top_clause["id"] if top_clause else None,
                "evidence_quote": top_clause["text_content"][:300] if top_clause else None,
                "confidence_score": 0.5,
                "analysis_notes": f"AI evaluation fallback: {str(e)[:100]}. Human review needed.",
            }

    @classmethod
    async def evaluate_version(
        cls,
        contract_version_id: uuid.UUID,
        db: AsyncSession,
    ) -> List[Finding]:
        """
        Evaluates all existing Requirements against a specific ContractVersion.
        Enforces 'No Silent Inheritance': every finding is freshly calculated.
        """
        # Fetch all requirements
        req_res = await db.execute(text("SELECT id, title, category, description, search_keywords FROM requirements;"))
        req_rows = req_res.fetchall()

        findings_created = []
        for r in req_rows:
            req_id, title, category, description, search_keywords = r[0], r[1], r[2], r[3], r[4] or []
            dummy_req = Requirement(id=req_id, title=title, category=category, description=description, search_keywords=search_keywords)

            # 1. Deterministic FTS retrieval
            candidates = await cls.find_candidate_clauses_fts(
                contract_version_id=contract_version_id,
                keywords=search_keywords,
                fallback_query=title,
                db=db,
            )

            # 2. Semantic evaluation via Gemini
            eval_result = await cls.evaluate_requirement_with_ai(dummy_req, candidates)

            # 3. Create or update finding for this version
            finding = Finding(
                requirement_id=req_id,
                contract_version_id=contract_version_id,
                status=eval_result["status"],
                evidence_clause_id=eval_result["evidence_clause_id"],
                evidence_quote=eval_result["evidence_quote"],
                confidence_score=eval_result["confidence_score"],
                analysis_notes=eval_result["analysis_notes"],
                review_status=ReviewStatus.PROPOSED,
            )
            # Remove any previous finding for this exact pair
            del_sql = text("DELETE FROM findings WHERE requirement_id = :rid AND contract_version_id = :vid;")
            await db.execute(del_sql, {"rid": req_id, "vid": contract_version_id})

            db.add(finding)
            findings_created.append(finding)

        await db.flush()
        return findings_created

