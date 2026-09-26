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
MID_SIZE = re.compile(r"중소기업|중기업|중\W?소기업")    # 중·소기업 is written with several middle dots
SMALL_SIZE = re.compile(r"소기업|소상공인")
# Law, regulation and agency names carry 중소기업 without admitting 중기업: 「중소기업기본법」, 중소기업 범위 및
# 확인에 관한 규정, 중소기업제품 구매촉진 … 법률. They are cut before the size class is read.
TITLES = re.compile(r"[「｢『《\"“‘'][^」｣』》\"”’']{0,60}[」｣』》\"”’']"
                    r"|중소기업\s*기본법|중소기업\s*범위\s*및\s*확인에\s*관한\s*규정|중소기업청|중소벤처기업부"
                    r"|\(\s*중소기업자의\s*범위\s*\)"
                    r"|중소기업제품[^,，.。]{0,30}?(?:법률|시행령|운영요령|종합정보망|구매정보망)")
EXCEPTION_TEXT = re.compile(r"우선\s*조달\s*계약?\s*(?:에\s*대한|의)?\s*예외|제\s*2\s*조\s*의\s*3|중소기업자\s*간\s*경쟁\s*(?:입찰)?\s*의?\s*예외")
FACILITY_SCALE = re.compile(r"\d+\s*(?:명|인|대|개소|곳|㎡|평|톤)|모든|전국|각\s*(?:광역|시[·ㆍ]?도)")
LAW_CITED = re.compile(r"법률|법\s*제|법」|법｣|시행령|시행규칙|허가\s*기준|허가를|면허|등록")


def squash(text) -> str:
    return SPACE.sub("", str(text or ""))


PUNCT = re.compile(r"[\W_]+")


def quoted(text, rec) -> bool:
    """The copy is in the notice, ignoring whitespace — or, for 10+ characters, ignoring punctuation too
    (the labeler swaps middle dots and brackets: ㆍ/·/・, ｢/「)."""
    if not isinstance(text, str):
        return False
    if b11.in_notice(text, rec):
        return True
    flat = PUNCT.sub("", text)
    return len(flat) >= 10 and flat in PUNCT.sub("", script._body(rec))


def price(rec):
    return script.estimated_price(rec)


def products():
    if not script._PRODUCTS:
        script.load_sme_reference(str(ROOT / "open/data"))
    return script._PRODUCTS


# Korean compounds are head-final: "매트리스 동적 롤링시스템" is a system, not a 매트리스. A catalogue name names the
# purchased object only as the whole name or its last element, once procurement words and notes are cut off.
PROCUREMENT_TAIL = re.compile(r"(?:\([^)]*\)|\[[^\]]*\]|구매|구입|납품|제작|설치|교체|임차|조달|보급|및|등|\d+(?:식|대|개|EA))+$")
META_ITEM = re.compile(r"([^\[\],]+)\[\d{10}\]")


def object_heads(object_name, registered) -> list:
    heads = []
    for raw in [object_name, *META_ITEM.findall(str(registered or ""))]:
        name = squash(raw)
        while True:
            cut = PROCUREMENT_TAIL.sub("", name)
            if cut == name:
                break
            name = cut
        if name:
            heads.append(name)
    return heads


def competitive(f, rec) -> bool:
    """판로지원법 제7조 (L15): the object is a designated item — by registered or quoted code, or by name —
    and the item's 특이사항 price cap, if any, is not exceeded."""
    meta_codes = set(CODE10.findall(str((rec.get("meta") or {}).get("세부품명번호목록") or "")))
    quote_codes = set(CODE10.findall(str(f.get("dp_required_quote") or "")))
    quote_codes |= set(CODE10.findall(str(f.get("catalogue_service") or "")))
    names = object_heads(f.get("object_name"), (rec.get("meta") or {}).get("세부품명번호목록"))
    value = price(rec)
    for row in products():
        by_code = row["세부품명번호"] in meta_codes | quote_codes
        item = squash(row["세부품명"])
        by_name = len(item) >= 4 and any(name.endswith(item) for name in names)
        if not (by_code or by_name):
            continue
        cap = script.product_cap_won(row)
        if cap is None or value is None or value < cap:
            return True
    return False


def excepted(f, rec) -> bool:
    """L19 제2조의3② · L17②: the exception must be written in the notice. A copied sentence that drifted from
    the original still counts when the notice itself carries the exception wording."""
    return quoted(f.get("priority_exception_quote"), rec) or bool(EXCEPTION_TEXT.search(script._body(rec)))


# L17 판로지원법 시행령 제7조 is the exception to 중소기업자간 경쟁; 제2조의3 (L19) excepts general products from
# 우선조달 and does not lift a 경쟁제품's duties. `국가계약법 시행령 제7조의2` is a different clause.
COMPETITION_EXCEPTION = re.compile(r"판로\s*지원[^\n]{0,40}?시행령[」』｣\s]*제\s*7\s*조(?!\s*의)"
                                   r"|중소기업자\s*간\s*경쟁\s*(?:입찰)?\s*의?\s*예외")


def competition_excepted(f, rec) -> bool:
    quote = str(f.get("priority_exception_quote") or "")
    return (quoted(quote, rec) and bool(COMPETITION_EXCEPTION.search(quote))) \
        or bool(COMPETITION_EXCEPTION.search(script._body(rec)))


def mostly_quoted(text, rec, width=8, share=0.8) -> bool:
    """Most of the copy's 8-character fragments occur in the notice — a copy broken by line wraps and dropped
    digits (`제 조제 항` / `2 2`) is still the notice's sentence."""
    flat = PUNCT.sub("", str(text or ""))
    if len(flat) < 20:
        return False
    body = PUNCT.sub("", script._body(rec))
    pieces = [flat[i:i + width] for i in range(0, len(flat) - width + 1, width)]
    return sum(piece in body for piece in pieces) >= share * len(pieces)


def size_class(f, rec):
    """What the size requirement admits: 'sme' (중기업 included), 'small', or None when there is none."""
    quote = f.get("sme_limit_quote")
    if not (quoted(quote, rec) or mostly_quoted(quote, rec)):
        return None
    flat = squash(TITLES.sub(" ", str(quote)))
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
        # A stated scale (a number, "all regions") without a statute behind it; a permit standard of another
        # law is that law's requirement (L01 2호), not a scale the orderer chose.
        quote = str(item["quote"])
        if kind == "facility_or_staff_scale" and not small_private_quote(rec) \
                and FACILITY_SCALE.search(quote) and not LAW_CITED.search(quote):
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
    if not competitive(f, rec) or competition_excepted(f, rec) or quoted(f.get("dp_required_quote"), rec):
        return 0
    # L16①: 중소기업자간 경쟁 always; a 수의계약 only in the decree's cases (L29②) and from 1천만원 (L29①).
    # The notice rarely says which 수의계약 ground it uses, so a 수의계약 is not read as v10.
    return int(not str((rec.get("meta") or {}).get("계약방법") or "").startswith("수의"))


def v11(f, rec):
    """L15 제7조①: a 경쟁제품 is bought from 중소기업자 only, unless an exception is stated (L17②)."""
    return int(competitive(f, rec) and not competition_excepted(f, rec) and size_class(f, rec) is None)


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
    # A stated 제2조의3 exception takes the notice out of 우선조달 altogether, so the bands do not bind (L19).
    return int(general and value is not None and value < 100_000_000 and size_class(f, rec) == "sme"
               and not excepted(f, rec))


def v18(f, rec):
    general, value = general_band(f, rec)
    return int(general and value is not None and value < 100_000_000
               and size_class(f, rec) is None and not excepted(f, rec))


def v20(f, rec):
    """L25 지침 제3조②: a software project states whether the large-company floor applies."""
    service = "용역" in str((rec.get("meta") or {}).get("업무구분") or "")
    return int(service and quoted(f.get("sw_scope_quote"), rec) and not quoted(f.get("large_firm_floor_quote"), rec))


VERDICTS = {"v1": v1, "v4": v4, "v9": b11.v9, "v10": v10, "v11": v11, "v16": v16, "v17": v17,
            "v18": v18, "v19": b11.v19, "v20": v20, "v24": b11.v24}
TEXT = (str, type(None))
SCHEMA = {
    "v1_restrictions": [{"quote": str, "kind": str, "private_firms_allowed": bool}],
    "v4_performance": [{"quote": str, "ordered_by": TEXT}],
    "v9_named": [str], "object_name": TEXT, "catalogue_service": TEXT, "dp_required_quote": TEXT,
    "sme_limit_quote": TEXT,
    "priority_exception_quote": TEXT, "v19_documents": [b11.V19_DOCUMENT], "sw_scope_quote": TEXT,
    "large_firm_floor_quote": TEXT, "v24_method_text": TEXT, "v24_region_text": TEXT,
    "v24_industry_texts": [str], "v24_amounts": [{"text": str, "label": str, "won": int}], "정보부족": bool,
}
KEYS = [*SCHEMA, "정보부족_사유"]

if __name__ == "__main__":
    raise SystemExit(harness.main(verdicts=VERDICTS, schema=SCHEMA))
