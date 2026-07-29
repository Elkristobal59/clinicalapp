"""Step 2 — locate the eligibility-criteria section pages.

Two signals, combined:
  * TF-IDF density — each page is scored by how much it reads like *eligibility-
    criteria language*, using a profile built from the Chia exemplar pool. This
    rewards the real section (dense in criteria wording) over a table-of-contents
    or synopsis page that merely mentions "Inclusion Criteria" once.
  * Heading match — an eligibility section heading (Inclusion/Exclusion/
    Eligibility Criteria, fuzzy to survive OCR typos like "Eiligibility") on a
    short, non-TOC line boosts the page.

Weak or ambiguous matches set `needs_review` rather than guessing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from scripts.pdf_parser.extract import Page

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POOL = ROOT / "data/chia_exemplar_pool.jsonl"

# Eligibility-section headings. 'lig[ei]bility' tolerates OCR typos (e.g. "Eiligibility").
HEADING_RE = re.compile(
    r"(inclusion\s+criteria|exclusion\s+criteria|lig[ei]bility|"
    r"patient\s+selection|selection\s+criteria|study\s+population)",
    re.I,
)


@lru_cache(maxsize=4)
def eligibility_profile(pool_path: Path = DEFAULT_POOL, limit: int = 1500) -> str:
    """A big bag of eligibility-criteria language, from the Chia pool criteria."""
    texts: list[str] = []
    with open(pool_path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i >= limit:
                break
            texts.append(json.loads(line)["text"])
    return " ".join(texts)


def is_heading(line: str) -> bool:
    """A short, non-TOC line that names the eligibility section."""
    line = line.strip()
    if not line or len(line) > 60:
        return False
    if re.search(r"\.{3,}", line):  # TOC dotted leader: "Inclusion Criteria .... 15"
        return False
    if re.search(r"\d{1,3}\s*$", line) and "criteria" in line.lower():  # trailing page no.
        return False
    return bool(HEADING_RE.search(line))


@dataclass
class Localization:
    ranked: list[tuple[int, float]]  # (page_number, score), best first
    section_pages: list[int]  # chosen contiguous page span
    heading_pages: list[int]  # pages with an eligibility heading
    confidence: float  # score of the best page
    needs_review: bool
    reason: str


def _no_text(reason: str) -> Localization:
    return Localization(ranked=[], section_pages=[], heading_pages=[],
                        confidence=0.0, needs_review=True, reason=reason)


def locate_eligibility(pages: list[Page], pool_path: Path = DEFAULT_POOL) -> Localization:
    page_texts = [p.text for p in pages]
    if not any(t.strip() for t in page_texts):  # scanned/image-only PDF (no extractable text)
        return _no_text("no extractable text (scanned PDF?) — needs OCR")
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    try:
        X = vec.fit_transform(page_texts)  # (n_pages, V), L2-normalized rows
        q = vec.transform([eligibility_profile(pool_path)])  # (1, V)
    except ValueError:  # empty vocabulary (only stop words / no usable tokens)
        return _no_text("TF-IDF empty vocabulary — scanned/low-text PDF")
    tfidf = (X @ q.T).toarray().ravel()  # cosine similarity of each page to the profile
    tnorm = tfidf / (tfidf.max() + 1e-9)

    heading_count = np.array([sum(is_heading(l) for l in p.lines) for p in pages], dtype=float)
    heading_pages = [p.number for p, h in zip(pages, heading_count) if h > 0]
    boost = np.clip(heading_count, 0, 2) * 0.4  # capped heading boost

    score = tnorm + boost
    order = np.argsort(-score)
    ranked = [(pages[i].number, float(score[i])) for i in order]

    best = int(order[0])
    thr = 0.6 * score[best]
    best_pageno = pages[best].number
    section = sorted(
        {best_pageno}
        | {pages[j].number for j in range(len(pages))
           if abs(pages[j].number - best_pageno) <= 1 and score[j] >= thr}
    )

    top = float(score[best])
    second = float(score[order[1]]) if len(order) > 1 else 0.0
    needs_review, reason = False, "ok"
    if tfidf[best] < 0.05:
        needs_review, reason = True, "weak TF-IDF match — no page reads like eligibility criteria"
    elif not heading_pages:
        needs_review, reason = True, "no eligibility heading detected — TF-IDF-only guess"
    elif (top - second) < 0.1 and sum(1 for _, s in ranked if s > 0.8 * top) > 2:
        needs_review, reason = True, "ambiguous — several pages score similarly"

    return Localization(
        ranked=ranked[:10],
        section_pages=section,
        heading_pages=heading_pages,
        confidence=top,
        needs_review=needs_review,
        reason=reason,
    )
