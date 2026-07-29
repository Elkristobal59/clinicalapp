"""Steps 1-3 — protocol PDF -> narrowed eligibility-criteria section text.

    python -m cliner.pdf.pipeline data/chia_withpdf/trainset/NCT00183885_Prot_SAP_000.pdf
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from scripts.pdf_parser.boundary import Section, narrow_to_section
from scripts.pdf_parser.extract import Page, extract_pages
from scripts.pdf_parser.localize import DEFAULT_POOL, Localization, locate_eligibility


@dataclass
class Result:
    pdf: str
    pages: list[Page]
    localization: Localization
    section: Section

    @property
    def needs_review(self) -> bool:
        return self.localization.needs_review or self.section.needs_review


def locate_section(pdf_path: str | Path, pool_path: Path = DEFAULT_POOL) -> Result:
    pages = extract_pages(pdf_path)
    loc = locate_eligibility(pages, pool_path)
    sec = narrow_to_section(pages, loc.section_pages)
    return Result(pdf=str(pdf_path), pages=pages, localization=loc, section=sec)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--chars", type=int, default=1000, help="preview N chars of the section text")
    args = ap.parse_args()

    r = locate_section(args.pdf)
    loc, sec = r.localization, r.section
    print(f"pdf              : {Path(args.pdf).name}  ({len(r.pages)} pages)")
    print(f"top pages (score): " + ", ".join(f"p{n}:{s:.2f}" for n, s in loc.ranked[:5]))
    print(f"section pages    : {loc.section_pages}   heading pages: {loc.heading_pages}")
    print(f"localize review  : {loc.needs_review}  ({loc.reason})")
    print(f"boundary         : start p{sec.start_page}, end = {sec.end_reason}")
    print(f"boundary review  : {sec.needs_review}  ({sec.reason})")
    print(f"OVERALL needs_review: {r.needs_review}")
    print(f"\n--- section text ({len(sec.text)} chars), first {args.chars} ---\n")
    print(sec.text[: args.chars])


if __name__ == "__main__":
    main()
