"""
ClauseTrace Document Extraction Service.
Extracts contract text, preserving page numbers, section headers, and character offsets.
Supports PDF (PyMuPDF), DOCX (python-docx), and Plain Text.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import fitz  # PyMuPDF
import docx


class DocumentExtractor:
    @staticmethod
    def extract_document(file_path: str, mime_type: str) -> List[Dict[str, Any]]:
        """
        Extracts document into an ordered list of clauses/chunks with page provenance.
        """
        p = Path(file_path)
        ext = p.suffix.lower()

        if ext == ".pdf" or "pdf" in mime_type:
            return DocumentExtractor._extract_pdf(p)
        elif ext == ".docx" or "wordprocessing" in mime_type:
            return DocumentExtractor._extract_docx(p)
        else:
            return DocumentExtractor._extract_text(p)

    @staticmethod
    def _extract_pdf(path: Path) -> List[Dict[str, Any]]:
        doc = fitz.open(path)
        clauses: List[Dict[str, Any]] = []
        clause_idx = 1
        global_char_offset = 0

        # Pattern for section headers like "1. Term and Termination", "Section 2 - Notice", "ARTICLE III"
        section_pattern = re.compile(
            r"^(?:(?:\d+\.|\d+\.\d+|section\s+\d+|article\s+[ivx\d]+)\s+[A-Za-z\s]{3,50}|[A-Z\s]{4,40})$",
            re.IGNORECASE,
        )

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

            current_section = f"Page {page_num + 1}"

            for para in paragraphs:
                lines = para.split("\n")
                first_line = lines[0].strip()

                if section_pattern.match(first_line) and len(lines) > 1:
                    current_section = first_line
                    para_body = "\n".join(lines[1:]).strip()
                elif section_pattern.match(first_line):
                    current_section = first_line
                    para_body = para
                else:
                    para_body = para

                if not para_body:
                    continue

                start = global_char_offset
                end = start + len(para_body)
                global_char_offset = end + 2  # account for spacing

                clauses.append(
                    {
                        "clause_index": clause_idx,
                        "page_number": page_num + 1,
                        "section_title": current_section,
                        "text_content": para_body,
                        "char_start": start,
                        "char_end": end,
                    }
                )
                clause_idx += 1

        doc.close()

        # Fallback if document text is monolithic
        if not clauses:
            clauses.append(
                {
                    "clause_index": 1,
                    "page_number": 1,
                    "section_title": "Full Document",
                    "text_content": "No extractable text found or document is scanned.",
                    "char_start": 0,
                    "char_end": 48,
                }
            )

        return clauses

    @staticmethod
    def _extract_docx(path: Path) -> List[Dict[str, Any]]:
        doc = docx.Document(path)
        clauses: List[Dict[str, Any]] = []
        clause_idx = 1
        global_char_offset = 0
        current_section = "General Terms"

        # Approximate 500 words per page for page provenance in DOCX
        words_per_page = 400
        current_word_count = 0
        current_page = 1

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            word_count = len(text.split())
            current_word_count += word_count
            current_page = max(1, (current_word_count // words_per_page) + 1)

            # Check heading style
            if p.style and "Heading" in p.style.name:
                current_section = text
                continue

            start = global_char_offset
            end = start + len(text)
            global_char_offset = end + 2

            clauses.append(
                {
                    "clause_index": clause_idx,
                    "page_number": current_page,
                    "section_title": current_section,
                    "text_content": text,
                    "char_start": start,
                    "char_end": end,
                }
            )
            clause_idx += 1

        return clauses

    @staticmethod
    def _extract_text(path: Path) -> List[Dict[str, Any]]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        clauses: List[Dict[str, Any]] = []
        clause_idx = 1
        offset = 0

        for idx, para in enumerate(paragraphs, start=1):
            start = offset
            end = start + len(para)
            offset = end + 2
            page = (idx // 6) + 1

            clauses.append(
                {
                    "clause_index": clause_idx,
                    "page_number": page,
                    "section_title": f"Section {clause_idx}",
                    "text_content": para,
                    "char_start": start,
                    "char_end": end,
                }
            )
            clause_idx += 1

        return clauses
