"""B11 v2 — the labeler copies passages; code checks each is in the notice and decides.

v1 asked the labeler for categories and it misread generic 동등 sentences as named products and
non-pledge documents as pledges. v2 asks for the literal strings (question-b-facts-v2.md). This
version was designed after reading v1's dev disagreements, so its dev score is optimistic
(docs/tasks/b-facts-labeler.md).

    python -X utf8 experiments/b11_b_facts_v2_verdict.py --facts <facts.jsonl> [--model-csv <csv>]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import script  # noqa: E402
import b11_b_facts_verdict as v1  # noqa: E402

SPACE = re.compile(r"\s+")
PLEDGE_KIND = re.compile(r"공급|기술\s*지원|A\s*/?\s*S|유지\s*보수")
BID_STAGE = re.compile(r"입찰|투찰|개찰\s*전")
METHODS = ("제한경쟁", "일반경쟁", "지명경쟁", "수의")
CODE = re.compile(r"(?<!\d)(\d{4})(?!\d)")


def in_notice(text, rec) -> bool:
    """The copied string occurs in the notice documents, ignoring whitespace."""
    flat = SPACE.sub("", text or "")
    return bool(flat) and flat in SPACE.sub("", script._body(rec))


def v9(f, rec):
    return int(any(isinstance(name, str) and in_notice(name, rec) for name in f.get("v9_named") or []))


def v19(f, rec):
    for doc in f.get("v19_documents") or []:
        if not isinstance(doc, dict):
            continue
        name, timing = str(doc.get("name") or ""), doc.get("timing")
        if "확약" in name and PLEDGE_KIND.search(name) and isinstance(timing, str) \
                and in_notice(timing, rec) and BID_STAGE.search(timing):
            return 1
    return 0


def v24(f, rec):
    meta = rec.get("meta") or {}
    method_text = f.get("v24_method_text")
    if isinstance(method_text, str) and in_notice(method_text, rec):
        method = next((m for m in METHODS if m in SPACE.sub("", method_text)), None)
        if method and meta.get("계약방법") and not str(meta.get("계약방법")).startswith(method):
            return 1
    region_text = f.get("v24_region_text")
    text_limited = isinstance(region_text, str) and in_notice(region_text, rec)
    meta_limited = meta.get("지역제한여부") == "Y"
    if text_limited != meta_limited:
        return 1
    listed = str(meta.get("제한지역코드목록") or "")
    if text_limited and listed and "[" not in listed:
        regions = re.findall(script.WIDE_REGION, region_text)
        if regions and script._region_key(regions) != script._region_key(script._region_names(listed)):
            return 1
    registered = set(script.META_INDUSTRY.findall(str(meta.get("면허업종제한목록") or "")))
    for passage in f.get("v24_industry_texts") or []:
        if isinstance(passage, str) and in_notice(passage, rec):
            if any(code not in registered for code in CODE.findall(passage)):
                return 1
    amounts = [a for a in f.get("v24_amounts") or []
               if isinstance(a, dict) and isinstance(a.get("text"), str) and in_notice(a["text"], rec)]
    return v1.v24({"v24_amounts": amounts, "v24_region_restricted": "yes" if meta_limited else "no"}, rec)


VERDICTS = {"v9": v9, "v19": v19, "v24": v24}
TEXT = (str, type(None))
SCHEMA = {"v9_named": list, "v19_documents": list, "v24_method_text": TEXT, "v24_region_text": TEXT,
          "v24_industry_texts": list, "v24_amounts": list, "정보부족": bool}

if __name__ == "__main__":
    raise SystemExit(v1.main(verdicts=VERDICTS, schema=SCHEMA))
