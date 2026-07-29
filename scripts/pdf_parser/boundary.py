"""Step 3 — narrow the located pages to the eligibility-criteria section text.

Starts at the first eligibility heading and runs until the next numbered section
at a higher level (e.g. the section is `5.x`, so it ends at the first `6.` /
`7.` … heading). Numbering is read from the protocol's own outline; if it can't
be read, the section is flagged for review rather than guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from scripts.pdf_parser.extract import Page
from scripts.pdf_parser.localize import HEADING_RE

# Any numbered line start (used to read the section's own level near the heading).
NUM_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\.?\s")

# A *section heading* number, distinguished from a value ("60 mg/m2") or a bare
# page-number footer ("16"):
#   - a dotted number alone on its line ("6.0", "5.2.1") — must have a dot so a
#     bare page number does not match, or
#   - a number (dotted or not) followed by a Title-Case word ("6.0 Treatment").
_NUM_ONLY = re.compile(r"^\s*(\d+(?:\.\d+)+)\.?\s*$")
_NUM_TITLE = re.compile(r"^\s*(\d+(?:\.\d+)*)\.?\s+[A-Z]")


def section_number(line: str) -> str | None:
    """Return the dotted section number if `line` looks like a section heading."""
    m = _NUM_ONLY.match(line) or _NUM_TITLE.match(line)
    return m.group(1) if m else None


@dataclass
class Section:
    text: str  # narrowed eligibility-section text
    start_page: int
    end_reason: str  # how the end boundary was decided
    needs_review: bool
    reason: str


def _flatten(pages: list[Page], lo: int, hi: int) -> list[tuple[int, str]]:
    """(page_number, line) for pages [lo, hi], newlines preserved as list items."""
    out: list[tuple[int, str]] = []
    for p in pages:
        if lo <= p.number <= hi:
            for ln in p.text.split("\n"):
                out.append((p.number, ln.rstrip()))
    return out


def narrow_to_section(pages: list[Page], section_pages: list[int]) -> Section:
    if not section_pages:
        return Section("", -1, "none", True, "no located pages")

    lo, hi = min(section_pages), max(section_pages)
    lines = _flatten(pages, lo, hi + 1)  # +1 page to catch the closing boundary

    # start = first real eligibility heading
    start = next(
        (i for i, (_, ln) in enumerate(lines)
         if HEADING_RE.search(ln) and len(ln.strip()) < 60 and not re.search(r"\.{3,}", ln)),
        None,
    )
    if start is None:
        return Section("", lo, "none", True, "no eligibility heading in located pages")

    # top-level section number near the heading (e.g. '5' from '5.0'/'5.1')
    base = None
    for _, ln in lines[start : start + 6]:
        m = NUM_RE.match(ln)
        if m:
            base = m.group(1).split(".")[0]
            break

    # end = next *section heading* whose top level is greater than `base`
    # (section_number ignores values like "60 mg/m2" that merely start with a digit)
    end, end_reason = len(lines), "reached end of located pages"
    if base and base.isdigit():
        for i in range(start + 1, len(lines)):
            num = section_number(lines[i][1])
            if num:
                top = num.split(".")[0]
                if top.isdigit() and int(top) > int(base):
                    end, end_reason = i, f"next section {lines[i][1].strip()[:30]!r}"
                    break

    text = "\n".join(ln for _, ln in lines[start:end]).strip()
    reasons: list[str] = []
    if base is None:
        reasons.append("unreadable section numbering (used heading→page-end)")
    if len(text) < 150:
        reasons.append(f"section text very short ({len(text)} chars) — likely mislocated")
    return Section(
        text=text,
        start_page=lines[start][0],
        end_reason=end_reason,
        needs_review=bool(reasons),
        reason="; ".join(reasons) if reasons else "ok",
    )
