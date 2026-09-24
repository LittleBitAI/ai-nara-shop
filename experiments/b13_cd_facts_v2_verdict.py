"""B13 v2 — v1/v2/v18 with passage placement decided by code from the copied heading.

Built after reading v1's dev disagreements, so dev scores are optimistic
(docs/tasks/b-facts-labeler-cd.md).

    python -X utf8 experiments/b13_cd_facts_v2_verdict.py --facts <facts.jsonl> [--model-csv <csv>]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import b13_cd_facts_verdict as v1  # noqa: E402
import b11_b_facts_verdict as table  # noqa: E402

EVALUATION = re.compile(r"평\s*가|배\s*점|심\s*사|점\s*수")
POINTS = re.compile(r"\d+(?:\.\d+)?\s*점(?![검수])")
DOCUMENT_LIST = re.compile(r"(?:제출|구비|첨부|증빙)\s*서\s*류")
COPIES = re.compile(r"\d+\s*부\s*[.)]?\s*$")
LOCATION = re.compile(r"소\s*재\s*지|영\s*업\s*소")
G2B = re.compile(r"나라장터|국가종합전자조달|입찰\s*참가\s*자격\s*등록")


def placed(entries, rec, *, v1_only=False):
    """Copied passages that sit in eligibility: not a scoring table, not a document list."""
    out = []
    for entry in entries or []:
        if not isinstance(entry, dict) or not isinstance(entry.get("text"), str):
            continue
        text, heading = entry["text"], str(entry.get("heading") or "")
        if not v1.in_notice(text, rec):
            continue
        if EVALUATION.search(heading) or POINTS.search(text):
            continue
        if DOCUMENT_LIST.search(heading) or COPIES.search(text):
            continue
        if v1_only and (LOCATION.search(text) or G2B.search(text)):
            continue
        out.append(text)
    return out


def as_v1_facts(f, rec):
    """Project v2 facts onto v1's keys so v1's verdicts apply unchanged."""
    return {"performance_texts": placed(f.get("performance"), rec),
            "institution_texts": placed(f.get("institution"), rec, v1_only=True),
            "sme_texts": placed(f.get("sme"), rec),
            "exception_texts": f.get("exception_texts") or [],
            "purchased_products": f.get("purchased_products") or []}


VERDICTS = {item: (lambda fn: lambda f, rec: fn(as_v1_facts(f, rec), rec))(v1.VERDICTS[item])
            for item in ("v1", "v2", "v18")}

if __name__ == "__main__":
    raise SystemExit(table.main(verdicts=VERDICTS))
