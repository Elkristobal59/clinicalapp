#!/usr/bin/env python3
"""
Script : remap_offsets.py (Phase 5 du Pipeline MLOps - Post-Processing)
-----------------------------------------------------------------------
Rôle : Recalculer les coordonnées (Offsets) des mots extraits par l'IA pour qu'ils correspondent 
exactement au texte d'origine, permettant ainsi de créer un fichier d'annotation standard (.ann).

🎓 Explication pour le jury (Le défi du Post-Processing) :
Quand Qwen (notre IA) génère du JSON, il nous dit : "J'ai trouvé le mot 'Diabète' qui est une Maladie".
Problème : Le logiciel de visualisation médical (ou Streamlit) a besoin de savoir OÙ se trouve le mot.
Il a besoin de coordonnées mathématiques : "Diabète commence au caractère 145 et finit au 152".
Mais comme l'IA a lu un résumé du texte (chunk), ses coordonnées sont faussées !

Ce script est un "Moteur d'Alignement Mathématique" :
1. Il prend le texte généré par l'IA.
2. Il le compare au texte PDF original brut.
3. Il fait glisser une fenêtre (SequenceMatcher) pour retrouver la position exacte du mot.
4. Il génère un fichier `.ann` standardisé (Format Brat) avec les vraies coordonnées absolues.
C'est indispensable pour évaluer scientifiquement le modèle avec l'outil de référence (Brateval).
"""

import argparse
import bisect
import csv
import difflib
import os
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ------------------------------------------------------------------------- #
# Data structures
# ------------------------------------------------------------------------- #

@dataclass
class Entity:
    id: str
    etype: str
    start: int
    end: int
    text: str
    fragments: Optional[List[Tuple[int, int]]] = None  # for discontinuous spans

    def to_ann_line(self) -> str:
        if self.fragments and len(self.fragments) > 1:
            span_str = ";".join(f"{s} {e}" for s, e in self.fragments)
        else:
            span_str = f"{self.start} {self.end}"
        return f"{self.id}\t{self.etype} {span_str}\t{self.text}"


@dataclass
class AlignmentReport:
    doc_id: str
    matched: bool
    match_ratio: float
    total_entities: int
    in_region: int
    dropped_out_of_region: int
    dropped_boundary_straddle: int
    remapped: int
    text_mismatch: int


# ------------------------------------------------------------------------- #
# .ann parsing / writing
# ------------------------------------------------------------------------- #

T_LINE_RE = re.compile(r"^(T\d+)\t(\S+) (.+?)\t(.*)$")


def parse_ann(path: str) -> Tuple[List[Entity], List[str]]:
    """Parse a brat .ann file. Returns (entities, other_lines).
    other_lines holds R/A/E/#/* lines verbatim (not remapped)."""
    entities = []
    other_lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line.strip():
                continue
            if line.startswith("T"):
                m = T_LINE_RE.match(line)
                if not m:
                    print(f"WARNING: could not parse T-line, passing through: {line}",
                          file=sys.stderr)
                    other_lines.append(line)
                    continue
                eid, etype, span_str, text = m.groups()
                fragments = []
                for part in span_str.split(";"):
                    s, e = part.split()
                    fragments.append((int(s), int(e)))
                start = fragments[0][0]
                end = fragments[-1][1]
                entities.append(Entity(eid, etype, start, end, text, fragments))
            else:
                other_lines.append(line)
    return entities, other_lines


def write_ann(path: str, entities: List[Entity], other_lines: List[str],
              keep_relations: bool) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ent in entities:
            f.write(ent.to_ann_line() + "\n")
        if keep_relations:
            for line in other_lines:
                f.write(line + "\n")


# ------------------------------------------------------------------------- #
# Normalization + alignment
# ------------------------------------------------------------------------- #

WS_RE = re.compile(r"\s+")
BULLET_RE = re.compile(r"^[\s]*[-*\u2022\u25cf\u2023\u2043]+\s*", re.MULTILINE)


def normalize_with_map(text: str) -> Tuple[str, List[int]]:
    """Collapse whitespace runs to a single space and strip leading bullet
    characters, while keeping a mapping from each character in the
    normalized string back to its index in the original string.
    Returns (normalized_text, index_map) where index_map[i] is the original
    offset of normalized_text[i].
    """
    # Strip common bullet markers first, tracking positions is easier if we
    # do a single pass character-by-character instead of chained regex subs.
    norm_chars = []
    index_map = []

    i = 0
    n = len(text)
    prev_was_space = True  # treat start-of-text as if preceded by whitespace
    while i < n:
        ch = text[i]
        if ch in " \t\r\n\f\v":
            if not prev_was_space:
                norm_chars.append(" ")
                index_map.append(i)
                prev_was_space = True
            i += 1
            continue
        # collapse bullet glyphs directly following whitespace/start
        if prev_was_space and ch in "-*\u2022\u25cf\u2023\u2043":
            i += 1
            continue
        norm_chars.append(ch)
        index_map.append(i)
        prev_was_space = False
        i += 1

    # trim trailing space
    while norm_chars and norm_chars[-1] == " ":
        norm_chars.pop()
        index_map.pop()
    # trim leading space
    start_trim = 0
    while start_trim < len(norm_chars) and norm_chars[start_trim] == " ":
        start_trim += 1
    norm_chars = norm_chars[start_trim:]
    index_map = index_map[start_trim:]

    return "".join(norm_chars), index_map


def build_alignment(full_text: str, snippet_text: str):
    """Align snippet_text against full_text on normalized forms.
    Returns:
      matching_blocks: list of (a_start, b_start, size) in NORMALIZED coords,
                        a = full, b = snippet, sorted by a_start.
      norm_full, map_full, norm_snip, map_snip, match_ratio
    """
    norm_full, map_full = normalize_with_map(full_text)
    norm_snip, map_snip = normalize_with_map(snippet_text)

    sm = difflib.SequenceMatcher(a=norm_full, b=norm_snip, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size > 0]
    match_ratio = sum(b.size for b in blocks) / max(len(norm_snip), 1)

    return blocks, norm_full, map_full, norm_snip, map_snip, match_ratio


class OffsetMapper:
    """Maps an original full-document character offset to an original
    gold-snippet character offset, using the matching blocks from
    build_alignment(). Offsets that fall outside any matching block return
    None (meaning: not part of the matched gold region)."""

    def __init__(self, blocks, map_full, map_snip):
        # blocks are in normalized coords: a=full, b=snippet
        # convert block boundaries to ORIGINAL full-doc coords for fast lookup
        self.block_orig_starts = []   # original full-doc start of each block
        self.block_orig_ends = []     # original full-doc end (exclusive) of each block
        self.blocks = blocks
        self.map_full = map_full
        self.map_snip = map_snip
        for blk in blocks:
            a0, a1 = blk.a, blk.a + blk.size - 1
            self.block_orig_starts.append(map_full[a0])
            self.block_orig_ends.append(map_full[a1] + 1)

    def full_offset_to_gold(self, orig_offset: int) -> Optional[int]:
        """Return the corresponding original offset in the gold snippet text,
        or None if orig_offset isn't inside any aligned block."""
        idx = bisect.bisect_right(self.block_orig_starts, orig_offset) - 1
        if idx < 0 or idx >= len(self.blocks):
            return None
        blk = self.blocks[idx]
        if orig_offset >= self.block_orig_ends[idx]:
            return None
        # Find normalized full-offset within the block via linear scan of
        # the tiny per-block original->normalized span (blocks are usually
        # short relative to the whole doc; for long blocks we binary search
        # the map_full slice instead).
        a0 = blk.a
        a1 = blk.a + blk.size  # exclusive, normalized coords
        lo, hi = a0, a1 - 1
        # binary search map_full[lo:hi+1] for orig_offset
        while lo < hi:
            mid = (lo + hi) // 2
            if self.map_full[mid] < orig_offset:
                lo = mid + 1
            else:
                hi = mid
        norm_full_idx = lo
        if self.map_full[norm_full_idx] != orig_offset:
            return None
        norm_snip_idx = norm_full_idx - blk.a + blk.b
        if norm_snip_idx < 0 or norm_snip_idx >= len(self.map_snip):
            return None
        return self.map_snip[norm_snip_idx]


# ------------------------------------------------------------------------- #
# Core remap routine for a single document pair
# ------------------------------------------------------------------------- #

def remap_document(full_txt_path: str, full_ann_path: str, gold_txt_path: str,
                    out_ann_path: str, keep_relations: bool = False,
                    min_match_ratio: float = 0.5) -> AlignmentReport:
    doc_id = os.path.basename(out_ann_path)

    with open(full_txt_path, "r", encoding="utf-8") as f:
        full_text = f.read()
    with open(gold_txt_path, "r", encoding="utf-8") as f:
        gold_text = f.read()

    blocks, norm_full, map_full, norm_snip, map_snip, match_ratio = \
        build_alignment(full_text, gold_text)

    if match_ratio < min_match_ratio:
        print(f"WARNING [{doc_id}]: low alignment ratio ({match_ratio:.2f}) "
              f"between full doc and gold snippet -- check that the gold "
              f"snippet actually comes from this protocol.", file=sys.stderr)

    mapper = OffsetMapper(blocks, map_full, map_snip)

    entities, other_lines = parse_ann(full_ann_path)

    out_entities = []
    n_dropped_out = 0
    n_dropped_straddle = 0
    n_mismatch = 0

    for ent in entities:
        new_fragments = []
        ok = True
        for (s, e) in (ent.fragments or [(ent.start, ent.end)]):
            gold_s = mapper.full_offset_to_gold(s)
            gold_e_inclusive = mapper.full_offset_to_gold(e - 1)
            if gold_s is None or gold_e_inclusive is None:
                ok = False
                break
            new_fragments.append((gold_s, gold_e_inclusive + 1))

        if not ok:
            # could be genuinely outside the region, or the start/end straddle
            # a boundary where alignment breaks down mid-entity
            partial_hit = mapper.full_offset_to_gold(ent.start) is not None or \
                           mapper.full_offset_to_gold(ent.end - 1) is not None
            if partial_hit:
                n_dropped_straddle += 1
            else:
                n_dropped_out += 1
            continue

        new_start = new_fragments[0][0]
        new_end = new_fragments[-1][1]
        new_text = gold_text[new_start:new_end]

        # sanity check: remapped text should match (mod whitespace) original
        if normalize_with_map(new_text)[0] != normalize_with_map(ent.text)[0]:
            n_mismatch += 1
            print(f"WARNING [{doc_id}] {ent.id}: remapped text mismatch: "
                  f"orig={ent.text!r} remapped={new_text!r}", file=sys.stderr)

        out_entities.append(Entity(ent.id, ent.etype, new_start, new_end,
                                    new_text, new_fragments))

    write_ann(out_ann_path, out_entities, other_lines, keep_relations)

    return AlignmentReport(
        doc_id=doc_id,
        matched=match_ratio >= min_match_ratio,
        match_ratio=match_ratio,
        total_entities=len(entities),
        in_region=len(out_entities),
        dropped_out_of_region=n_dropped_out,
        dropped_boundary_straddle=n_dropped_straddle,
        remapped=len(out_entities),
        text_mismatch=n_mismatch,
    )


# ------------------------------------------------------------------------- #
# Batch mode: match files by NCT id
# ------------------------------------------------------------------------- #

NCT_RE = re.compile(r"(NCT\d+)")


def extract_nct_id(filename: str) -> Optional[str]:
    m = NCT_RE.search(filename)
    return m.group(1) if m else None


def run_batch(full_txt_dir: str, full_ann_dir: str, gold_txt_dir: str,
              out_dir: str, keep_relations: bool, min_match_ratio: float,
              report_csv: Optional[str]) -> None:
    full_txt_by_nct = {}
    for fn in os.listdir(full_txt_dir):
        if fn.endswith(".txt"):
            nct = extract_nct_id(fn)
            if nct:
                full_txt_by_nct[nct] = os.path.join(full_txt_dir, fn)

    full_ann_by_nct = {}
    for fn in os.listdir(full_ann_dir):
        if fn.endswith(".ann"):
            nct = extract_nct_id(fn)
            if nct:
                full_ann_by_nct[nct] = os.path.join(full_ann_dir, fn)

    gold_txt_files = [fn for fn in os.listdir(gold_txt_dir) if fn.endswith(".txt")]

    reports = []
    n_skipped = 0
    for gold_fn in sorted(gold_txt_files):
        nct = extract_nct_id(gold_fn)
        if not nct:
            print(f"SKIP: could not extract NCT id from gold file {gold_fn}",
                  file=sys.stderr)
            n_skipped += 1
            continue
        if nct not in full_txt_by_nct or nct not in full_ann_by_nct:
            print(f"SKIP: no matching full-protocol txt/ann for {nct} "
                  f"(gold file {gold_fn})", file=sys.stderr)
            n_skipped += 1
            continue

        gold_txt_path = os.path.join(gold_txt_dir, gold_fn)
        full_txt_path = full_txt_by_nct[nct]
        full_ann_path = full_ann_by_nct[nct]
        out_ann_path = os.path.join(out_dir, gold_fn.replace(".txt", ".ann"))

        try:
            report = remap_document(full_txt_path, full_ann_path, gold_txt_path,
                                     out_ann_path, keep_relations, min_match_ratio)
            reports.append(report)
        except Exception as exc:  # keep batch going even if one doc fails
            print(f"ERROR processing {gold_fn}: {exc}", file=sys.stderr)
            n_skipped += 1

    # also copy gold .txt alongside remapped .ann so brateval's folder has
    # matching .txt/.ann pairs if it needs the text (some brat tools do)
    for gold_fn in gold_txt_files:
        nct = extract_nct_id(gold_fn)
        if nct in full_txt_by_nct:
            src = os.path.join(gold_txt_dir, gold_fn)
            dst = os.path.join(out_dir, gold_fn)
            if not os.path.exists(dst):
                with open(src, "r", encoding="utf-8") as fin, \
                     open(dst, "w", encoding="utf-8") as fout:
                    fout.write(fin.read())

    print(f"\nProcessed {len(reports)} documents, skipped {n_skipped}.\n")
    print(f"{'doc_id':40s} {'match%':>7s} {'total':>6s} {'kept':>6s} "
          f"{'drop_out':>9s} {'drop_edge':>10s} {'mismatch':>9s}")
    for r in reports:
        print(f"{r.doc_id:40s} {r.match_ratio*100:6.1f}% {r.total_entities:6d} "
              f"{r.remapped:6d} {r.dropped_out_of_region:9d} "
              f"{r.dropped_boundary_straddle:10d} {r.text_mismatch:9d}")

    if report_csv:
        with open(report_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["doc_id", "match_ratio", "total_entities", "kept",
                        "dropped_out_of_region", "dropped_boundary_straddle",
                        "text_mismatch"])
            for r in reports:
                w.writerow([r.doc_id, f"{r.match_ratio:.4f}", r.total_entities,
                            r.remapped, r.dropped_out_of_region,
                            r.dropped_boundary_straddle, r.text_mismatch])
        print(f"\nPer-document report written to {report_csv}")


# ------------------------------------------------------------------------- #
# CLI
# ------------------------------------------------------------------------- #

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--batch", action="store_true",
                    help="Batch mode over directories, matched by NCT id.")

    # single-doc mode
    p.add_argument("--full-txt", help="Full protocol .txt (single-doc mode)")
    p.add_argument("--full-ann", help="System .ann on full protocol (single-doc mode)")
    p.add_argument("--gold-txt", help="Chia gold snippet .txt (single-doc mode)")
    p.add_argument("--out-ann", help="Output remapped .ann path (single-doc mode)")

    # batch mode
    p.add_argument("--full-txt-dir")
    p.add_argument("--full-ann-dir")
    p.add_argument("--gold-txt-dir")
    p.add_argument("--out-dir")
    p.add_argument("--report-csv", default=None,
                    help="Optional path to write a per-document alignment report CSV")

    p.add_argument("--keep-relations", action="store_true",
                    help="Pass through R/A/E/#/* lines unchanged into the output "
                         "(their offsets, if any, are NOT remapped -- use with "
                         "caution, mainly useful to keep attribute lines like "
                         "negation flags that don't carry offsets).")
    p.add_argument("--min-match-ratio", type=float, default=0.5,
                    help="Warn if the fraction of the gold snippet found in the "
                         "full document falls below this (default 0.5).")

    args = p.parse_args()

    if args.batch:
        missing = [n for n in ("full_txt_dir", "full_ann_dir", "gold_txt_dir", "out_dir")
                   if getattr(args, n) is None]
        if missing:
            p.error(f"--batch requires: {', '.join('--' + m.replace('_','-') for m in missing)}")
        os.makedirs(args.out_dir, exist_ok=True)
        run_batch(args.full_txt_dir, args.full_ann_dir, args.gold_txt_dir,
                  args.out_dir, args.keep_relations, args.min_match_ratio,
                  args.report_csv)
    else:
        missing = [n for n in ("full_txt", "full_ann", "gold_txt", "out_ann")
                   if getattr(args, n) is None]
        if missing:
            p.error(f"single-doc mode requires: "
                    f"{', '.join('--' + m.replace('_','-') for m in missing)}")
        report = remap_document(args.full_txt, args.full_ann, args.gold_txt,
                                 args.out_ann, args.keep_relations,
                                 args.min_match_ratio)
        print(f"Alignment ratio: {report.match_ratio*100:.1f}%")
        print(f"Entities in full-doc system output: {report.total_entities}")
        print(f"Entities kept (inside matched region): {report.remapped}")
        print(f"Entities dropped (outside region): {report.dropped_out_of_region}")
        print(f"Entities dropped (boundary straddle): {report.dropped_boundary_straddle}")
        print(f"Entities with text mismatch after remap: {report.text_mismatch}")
        print(f"Written: {args.out_ann}")


if __name__ == "__main__":
    main()
