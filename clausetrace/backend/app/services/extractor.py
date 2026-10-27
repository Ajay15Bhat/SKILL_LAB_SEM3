"""
ClauseTrace PDF Text Extraction & Clause Segmentation Engine.
Powered by PyMuPDF (fitz) for sub-second, page-aware text chunking.
"""

import re
import uuid
from pathlib import Path
from typing import List, Optional
import pymupdf as fitz
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Clause


class PDFExtractorService:
    """
    Extracts text from PDF documents page by page, segmenting the text into
    logical clauses and detecting section titles.
    """

    # Regex patterns for detecting common legal section headers
    SECTION_HEADER_PATTERN = re.compile(
        r"^(?:(?:section|article|clause)\s+\d+[:.]?|\d+[\.\)]\s+|[A-Z\s]{4,}:)",
        re.IGNORECASE,
    )

    @classmethod
    async def extract_and_store_clauses(
        cls,
        pdf_path: str,
        contract_version_id: uuid.UUID,
        db: AsyncSession,
    ) -> List[Clause]:
        """
        Extracts paragraphs and clauses from a PDF file, preserving page numbers,
        and saves them directly into the 'clauses' database table.
        """
        doc = fitz.open(pdf_path)
        clauses_to_insert = []
        clause_index = 1
        current_section: Optional[str] = None
        global_char_offset = 0

        for page_num in range(len(doc)):
            page = doc[page_num]
            # Extract text blocks: (x0, y0, x1, y1, text, block_no, block_type)
            blocks = page.get_text("blocks")

            for block in blocks:
                # Filter out image blocks (type 1)
                if len(block) >= 7 and block[6] != 0:
                    continue

                raw_text = block[4].strip()
                if not raw_text:
                    continue

                # Clean up repeated whitespace
                cleaned_text = re.sub(r"\s+", " ", raw_text).strip()
                if len(cleaned_text) < 15:  # Ignore tiny artifacts/headers/page numbers
                    continue

                # Check if first line matches a section header
                first_line = cleaned_text.split(".")[0].strip()
                if cls.SECTION_HEADER_PATTERN.match(first_line) or (
                    len(first_line) < 60 and first_line.isupper()
                ):
                    current_section = first_line[:100]

                char_start = global_char_offset
                char_end = char_start + len(cleaned_text)
                global_char_offset = char_end + 1

                clause = Clause(
                    contract_version_id=contract_version_id,
                    clause_index=clause_index,
                    page_number=page_num + 1,
                    section_title=current_section,
                    text_content=cleaned_text,
                    char_start=char_start,
                    char_end=char_end,
                )
                clauses_to_insert.append(clause)
                clause_index += 1

        doc.close()

        # Bulk save to PostgreSQL
        if clauses_to_insert:
            db.add_all(clauses_to_insert)
            await db.flush()

        return clauses_to_insert
