"""labels-600 focused labeler for v1, v10 and v20 — the three excluded items whose block was the question,
not the dev labels (docs/tasks/labels-600.md). v9 and v24 stay excluded: two independent labelers agree on the
same cells against dev there.

Question: reports/labels-600/facts/question-focus.md. Written after reading the calib-120 errors, so the
calibration on those 120 is optimistic.

    python -X utf8 experiments/a_focus_verdict.py --facts <facts.jsonl>
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import a_facts_verdict as fv  # noqa: E402
import b11_b_facts_verdict as harness  # noqa: E402

TEXT = fv.TEXT


def contract(rec):
    meta = rec.get("meta") or {}
    return str(meta.get("적용계약법") or ""), str(meta.get("계약방법") or "")


def v1(f, rec):
    """국가 시행규칙 제17조 · 지방 시행규칙 제17조: nothing beyond 영 제12조/제13조 without a legal basis.
    Allowed without one: 지방 소액수의 견적 limited by staff or equipment the task needs (집행기준 제5장 1.6)
    라·마); a special facility or technology the goods or service needs (국가 영 제21조① 3·5호; S7-12:
    relevance alone does not clear 제한경쟁)."""
    law, method = contract(rec)
    small_quote = law == "지방계약법" and method.startswith("수의")
    for item in f.get("v1_limits") or []:
        if not isinstance(item, dict) or not fv.quoted(item.get("quote"), rec):
            continue
        if fv.quoted(item.get("statute_quote"), rec):
            continue
        kind = item.get("kind")
        if kind in ("institution_type", "named_organisation"):
            if item.get("private_firms_allowed") is False:
                return 1
            continue
        need = fv.quoted(item.get("need_quote"), rec)
        if small_quote and need:
            continue
        if need and fv.quoted(item.get("special_quote"), rec):
            continue
        if kind == "facility_equipment_staff" and not need:
            return 1
    return 0


def v10(f, rec):
    """판로지원법 제9조①: a 경쟁제품 bought by 중소기업자간 경쟁 needs 직접생산 확인 as a participation
    requirement (S7-15). A 수의계약 is not read as v10 (L29 cases are rarely stated)."""
    # competitive() also reads product codes out of the certificate sentence.
    if not fv.competitive({**f, "dp_required_quote": f.get("dp_participation_quote")}, rec) \
            or fv.excepted(f, rec) or fv.quoted(f.get("dp_participation_quote"), rec):
        return 0
    return int(not contract(rec)[1].startswith("수의"))


def v20(f, rec):
    """지침 제3조②: a software business (소프트웨어 진흥법 제2조 2·3호, bundled orders included — 지침 제2조②)
    states in 공고문 or 제안요청서 whether the large-company floor applies. A document only referred to is not
    input (S7-10), so it cannot supply the statement."""
    return int(fv.quoted(f.get("sw_project_quote"), rec)
               and not fv.quoted(f.get("sw_floor_statement_quote"), rec))


VERDICTS = {"v1": v1, "v10": v10, "v20": v20}
SCHEMA = {
    "v1_limits": [{"quote": str, "kind": str, "private_firms_allowed": bool, "statute_quote": TEXT,
                   "need_quote": TEXT, "special_quote": TEXT}],
    "object_name": TEXT, "catalogue_service": TEXT, "dp_participation_quote": TEXT, "dp_other_quote": TEXT,
    "priority_exception_quote": TEXT, "sw_project_quote": TEXT, "sw_floor_statement_quote": TEXT,
    "sw_referenced_missing": bool, "정보부족": bool,
}
KEYS = [*SCHEMA, "정보부족_사유"]

if __name__ == "__main__":
    raise SystemExit(harness.main(verdicts=VERDICTS, schema=SCHEMA))
