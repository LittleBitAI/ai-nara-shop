"""labels-600 fact labeler — the labeler copies passages, code decides each item by the provided clauses.

Covers the items the 24-item Luna labeler could not be trusted on (v1 v9 v10 v11 v18 v19 v20 v24) and the
conditional ones (v4 v16 v17). Question: reports/labels-600/facts/question-facts.md. The v9, v19 and v24
decisions are B11 v2's (experiments/b11_b_facts_v2_verdict.py). Clause IDs refer to
reports/labels-600/law-excerpt.txt.

    python -X utf8 experiments/a_facts_verdict.py --facts <facts.jsonl> [--model-csv <csv>]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import script  # noqa: E402
import b11_b_facts_verdict as harness  # noqa: E402
import b11_b_facts_v2_verdict as b11  # noqa: E402

SPACE = re.compile(r"\s+")
CODE10 = re.compile(r"(?<!\d)\d{10}(?!\d)")
PUBLIC_ORDERER = re.compile(r"국가|지방자치단체|지자체|공공기관|공기업|준정부|정부|관공서|행정기관")
MID_SIZE = re.compile(r"중소기업|중기업|중[·ㆍ‧∙.]?소기업")
SMALL_SIZE = re.compile(r"소기업|소상공인")
SMALL_QUOTE_FLOOR = 10_000_000          # L29①: 수의계약 직생 확인은 추정가격 1천만원 이상


def squash(text) -> str:
    return SPACE.sub("", str(text or ""))


def quoted(text, rec) -> bool:
    return isinstance(text, str) and b11.in_notice(text, rec)


def price(rec):
    return script.estimated_price(rec)


def products():
    if not script._PRODUCTS:
        script.load_sme_reference(str(ROOT / "open/data"))
    return script._PRODUCTS


def competitive(f, rec) -> bool:
    """판로지원법 제7조 (L15): the object is a designated item — by registered or quoted code, or by name —
    and the item's 특이사항 price cap, if any, is not exceeded."""
    meta_codes = set(CODE10.findall(str((rec.get("meta") or {}).get("세부품명번호목록") or "")))
    quote_codes = set(CODE10.findall(str(f.get("dp_required_quote") or "")))
    name = squash(f.get("object_name")) + squash((rec.get("meta") or {}).get("세부품명번호목록"))
    value = price(rec)
    for row in products():
        by_code = row["세부품명번호"] in meta_codes | quote_codes
        by_name = len(squash(row["세부품명"])) >= 4 and squash(row["세부품명"]) in name
        if not (by_code or by_name):
            continue
        cap = script.product_cap_won(row)
        if cap is None or value is None or value < cap:
            return True
    return False


def excepted(f, rec) -> bool:
    return quoted(f.get("priority_exception_quote"), rec)


def size_class(f, rec):
    """What the size requirement admits: 'sme' (중기업 included), 'small', or None when there is none."""
    quote = f.get("sme_limit_quote")
    if not quoted(quote, rec):
        return None
    flat = squash(quote)
    if MID_SIZE.search(flat):
        return "sme"
    return "small" if SMALL_SIZE.search(flat) else None


def small_private_quote(rec) -> bool:
    meta = rec.get("meta") or {}
    return meta.get("적용계약법") == "지방계약법" and str(meta.get("계약방법") or "").startswith("수의")


def v1(f, rec):
    """L01–L04: no participation requirement beyond 영 제12조/제13조 without a legal basis. 지방 소액수의 견적 may
    limit by equipment or facilities (L14 나.6))."""
    for item in f.get("v1_restrictions") or []:
        if not isinstance(item, dict) or not quoted(item.get("quote"), rec):
            continue
        kind = item.get("kind")
        if kind in ("institution_type", "named_organisation") and item.get("private_firms_allowed") is False:
            return 1
        if kind == "facility_or_staff_scale" and not small_private_quote(rec):
            return 1
    return 0


def v4(f, rec):
    """L12④3 · L13 1)5): 실적 accepted only from specific (public) orderers. No amount condition."""
    for item in f.get("v4_performance") or []:
        if not isinstance(item, dict) or not quoted(item.get("quote"), rec):
            continue
        orderer = item.get("ordered_by")
        if quoted(orderer, rec) and PUBLIC_ORDERER.search(squash(orderer)) and "민간" not in squash(item["quote"]):
            return 1
    return 0


def v10(f, rec):
    """L15 제7조① · L16①: a 경쟁제품 in 중소기업자간 경쟁 needs 직접생산 확인; a 수의계약 below 1천만원 does not (L29)."""
    if not competitive(f, rec) or excepted(f, rec) or quoted(f.get("dp_required_quote"), rec):
        return 0
    value = price(rec)
    meta = rec.get("meta") or {}
    if str(meta.get("계약방법") or "").startswith("수의") and value is not None and value < SMALL_QUOTE_FLOOR:
        return 0
    return 1


def v11(f, rec):
    """L15 제7조①: a 경쟁제품 is bought from 중소기업자 only, unless an exception is stated (L17②)."""
    return int(competitive(f, rec) and not excepted(f, rec) and size_class(f, rec) is None)


def general_band(f, rec):
    """(general-product scope?, price) for the v14–v18 table (L05 10호, L06 12호, L19)."""
    business = str((rec.get("meta") or {}).get("업무구분") or "")
    return (not competitive(f, rec) and "공사" not in business), price(rec)


def v16(f, rec):
    general, value = general_band(f, rec)
    return int(general and value is not None and 100_000_000 <= value < script.NOTICE_AMOUNT_WON
               and size_class(f, rec) is None and not excepted(f, rec))


def v17(f, rec):
    general, value = general_band(f, rec)
    return int(general and value is not None and value < 100_000_000 and size_class(f, rec) == "sme")


def v18(f, rec):
    general, value = general_band(f, rec)
    return int(general and value is not None and value < 100_000_000
               and size_class(f, rec) is None and not excepted(f, rec))


def v20(f, rec):
    """L25 지침 제3조②: a software project states whether the large-company floor applies."""
    return int(quoted(f.get("sw_scope_quote"), rec) and not quoted(f.get("large_firm_floor_quote"), rec))


VERDICTS = {"v1": v1, "v4": v4, "v9": b11.v9, "v10": v10, "v11": v11, "v16": v16, "v17": v17,
            "v18": v18, "v19": b11.v19, "v20": v20, "v24": b11.v24}
TEXT = (str, type(None))
SCHEMA = {
    "v1_restrictions": [{"quote": str, "kind": str, "private_firms_allowed": bool}],
    "v4_performance": [{"quote": str, "ordered_by": TEXT}],
    "v9_named": [str], "object_name": TEXT, "dp_required_quote": TEXT, "sme_limit_quote": TEXT,
    "priority_exception_quote": TEXT, "v19_documents": [b11.V19_DOCUMENT], "sw_scope_quote": TEXT,
    "large_firm_floor_quote": TEXT, "v24_method_text": TEXT, "v24_region_text": TEXT,
    "v24_industry_texts": [str], "v24_amounts": [{"text": str, "label": str, "won": int}], "정보부족": bool,
}
KEYS = [*SCHEMA, "정보부족_사유"]

if __name__ == "__main__":
    raise SystemExit(harness.main(verdicts=VERDICTS, schema=SCHEMA))
