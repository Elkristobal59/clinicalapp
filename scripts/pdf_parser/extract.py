"""Step 1 — extract paged text from a protocol PDF (page numbers preserved)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class Page:
    number: int  # 0-based page index
    text: str  # full page text as extracted
    lines: list[str]  # non-empty stripped lines (for heading detection)


def extract_pages(pdf_path: str | Path) -> list[Page]:
    """Return one `Page` per PDF page, preserving order/number."""
    doc = fitz.open(str(pdf_path))
    try:
        pages = []
        for i in range(doc.page_count):
            text = doc[i].get_text("text")
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            pages.append(Page(number=i, text=text, lines=lines))
        return pages
    finally:
        doc.close()
