"""Batch-run the PDF front-end over protocol PDFs and save the extracted
eligibility sections, split into clean/ vs review/, with a manifest.

    python -m cliner.pdf.batch                                  # trainset (default)
    python -m cliner.pdf.batch --pdf-dir data/chia_withpdf/testset
    python -m cliner.pdf.batch --pdf-dir data/chia_withpdf/trainset --pdf-dir data/chia_withpdf/testset

Output (default data/processed/eligibility_sections/):
    clean/<NCT>.txt      extracted section, no review flag
    review/<NCT>.txt     extracted section that needs a human look (may be empty)
    manifest.csv         one row per PDF: pages, section_pages, chars, incl/excl, review, reason
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from cliner.pdf.pipeline import locate_section

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PDF_DIR = ROOT / "data/chia_withpdf/trainset"
DEFAULT_OUT = ROOT / "data/processed/eligibility_sections"
NCT_RE = re.compile(r"NCT\d+")


def _nct(name: str) -> str:
    m = NCT_RE.search(name)
    return m.group(0) if m else Path(name).stem


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf-dir", type=Path, action="append", dest="pdf_dirs",
                    help="directory of *.pdf (repeatable); default data/chia_withpdf/trainset")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    pdf_dirs = args.pdf_dirs or [DEFAULT_PDF_DIR]
    pdfs = sorted(p for d in pdf_dirs for p in d.glob("*.pdf"))
    (args.out / "clean").mkdir(parents=True, exist_ok=True)
    (args.out / "review").mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    n_clean = n_review = n_err = 0
    for pdf in pdfs:
        nct = _nct(pdf.name)
        try:
            r = locate_section(pdf)
        except Exception as e:  # keep going; record the failure
            n_err += 1
            rows.append(dict(nct=nct, pdf=pdf.name, pages="", section_pages="", chars=0,
                             inclusion="", exclusion="", needs_review=True,
                             reason=f"ERROR {type(e).__name__}: {e}", file=""))
            continue

        text = r.section.text
        sub = "review" if r.needs_review else "clean"
        dest = args.out / sub / f"{nct}.txt"
        dest.write_text(text, encoding="utf-8")
        n_review += r.needs_review
        n_clean += not r.needs_review
        reason = r.localization.reason if r.localization.needs_review else r.section.reason
        rows.append(dict(
            nct=nct, pdf=pdf.name, pages=len(r.pages),
            section_pages="|".join(map(str, r.localization.section_pages)),
            chars=len(text),
            inclusion=bool(re.search(r"inclusion", text, re.I)),
            exclusion=bool(re.search(r"exclusion", text, re.I)),
            needs_review=r.needs_review, reason=reason,
            file=str(dest.relative_to(ROOT)),
        ))

    manifest = args.out / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"processed {len(pdfs)} pdfs -> {args.out}")
    print(f"  clean  : {n_clean}   -> {args.out / 'clean'}")
    print(f"  review : {n_review}   -> {args.out / 'review'}")
    if n_err:
        print(f"  errors : {n_err}")
    print(f"manifest : {manifest}")


if __name__ == "__main__":
    main()
