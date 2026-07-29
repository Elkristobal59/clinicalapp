"""Step 4 — segment a narrowed eligibility section into individual criteria (LLM).

Rule-based splitting mishandles real protocols (nested a/b/c sub-items, trailing
qualifier sentences, inconsistent numbering), so this asks the LLM to split the
section, copying each criterion verbatim. `generate` is a `str->str` callable
from `cliner.serve.vllm_client.make_generate(..., guided_json=SEGMENT_SCHEMA)`.
"""

from __future__ import annotations

import json
import re

# vLLM guided-decoding schema: a JSON array of criterion strings.
SEGMENT_SCHEMA = {"type": "array", "items": {"type": "string"}}


def build_segment_prompt(section_text: str) -> str:
    return (
        "You are given the eligibility-criteria section of a clinical trial protocol.\n"
        "Split it into individual criteria. Copy each criterion VERBATIM from the "
        "text — do not paraphrase, merge, renumber, or drop sub-items.\n"
        "Return a JSON array of strings, one criterion per element.\n\n"
        f"Section:\n{section_text}\n\nCriteria:"
    )


def segment_criteria(section_text: str, generate) -> list[str]:
    """Return the list of criterion strings the LLM split the section into."""
    raw = generate(build_segment_prompt(section_text))
    try:
        items = json.loads(re.search(r"\[.*\]", raw, re.S).group())
    except Exception:
        return []
    return [s.strip() for s in items if isinstance(s, str) and s.strip()]
