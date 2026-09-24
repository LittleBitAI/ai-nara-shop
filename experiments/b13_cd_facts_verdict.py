"""B13 — C/D weak items: the labeler copies passages, code decides with the operating helpers.

Mapping fixed in docs/tasks/b-facts-labeler-cd.md before any run. Scoring reuses B11's table.

    python -X utf8 experiments/b13_cd_facts_verdict.py --facts <facts.jsonl> [--model-csv <HEAD dev replay>]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import script  # noqa: E402
import b11_b_facts_verdict as table  # noqa: E402
from b11_b_facts_v2_verdict import in_notice  # noqa: E402

script.load_sme_reference(str(ROOT / "open/data"))      # fills script._PRODUCTS (catalog + caps)
CODE10 = re.compile(r"(?<!\d)(\d{10})(?!\d)")
SPACE = re.compile(r"\s+")
SMALL = re.compile(r"소\s*기\s*업|소\s*상\s*공\s*인")
NOTICE_WON = 230_000_000
HUNDRED_MILLION = 100_000_000
CATALOG = {SPACE.sub("", p["세부품명"]): p["세부품명번호"] for p in script._PRODUCTS if p.get("세부품명번호")}


def present(f, key, rec):
    return [t for t in f.get(key) or [] if isinstance(t, str) and in_notice(t, rec)]


def competitive(f, rec):
    meta = rec.get("meta") or {}
    codes = set(CODE10.findall(str(meta.get("세부품명번호목록") or "")))
    for name in f.get("purchased_products") or []:
        code = CATALOG.get(SPACE.sub("", str(name)))
        if code:
            codes.add(code)
    return script.competitive_product(rec, codes) is True


def local_small_negotiated(rec):
    meta = rec.get("meta") or {}
    price = script.estimated_price(rec)
    return ("지방" in str(meta.get("적용계약법") or "") and meta.get("계약방법") == "수의계약"
            and price is not None and price < HUNDRED_MILLION)


def v1(f, rec):
    return int(bool(present(f, "institution_texts", rec)))


def v2(f, rec):
    price = script.estimated_price(rec)
    return int(bool(present(f, "performance_texts", rec)) and price is not None and price < NOTICE_WON
               and not local_small_negotiated(rec))


def v10(f, rec):
    return int(competitive(f, rec) and not present(f, "direct_production_texts", rec))


def v11(f, rec):
    return int(competitive(f, rec) and not present(f, "sme_texts", rec))


def v13(f, rec):
    meta = rec.get("meta") or {}
    return int(competitive(f, rec) and meta.get("계약방법") != "수의계약"
               and any(script.v17_quote_is_narrow(t) for t in present(f, "sme_texts", rec)))


def v18(f, rec):
    price = script.estimated_price(rec)
    return int(price is not None and price < HUNDRED_MILLION and not competitive(f, rec)
               and not any(SMALL.search(t) for t in present(f, "sme_texts", rec))
               and not present(f, "exception_texts", rec))


VERDICTS = {"v1": v1, "v2": v2, "v10": v10, "v11": v11, "v13": v13, "v18": v18}

if __name__ == "__main__":
    raise SystemExit(table.main(verdicts=VERDICTS))
