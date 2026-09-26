"""labels-600 focused labeler for v1 and v20 — excluded items whose block was the question, not the dev labels
(docs/tasks/labels-600.md). v10 is the fact labeler's (a_facts_verdict.v10).

Question: reports/labels-600/facts/question-focus.md. Revised on all of dev 200, so its dev scores are fitted.

    python -X utf8 experiments/a_focus_verdict.py --facts <facts.jsonl>
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import a_facts_verdict as fv  # noqa: E402
import b11_b_facts_verdict as harness  # noqa: E402

TEXT = fv.TEXT
# Location and company-size limits are v5–v7 and v10–v18, not v1 — a backstop for copies the question excludes.
OTHER_ITEM_LIMIT = re.compile(r"소재지|영업소|본점|본사|지점|중소기업|중기업|소기업|소상공인")


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
        if OTHER_ITEM_LIMIT.search(fv.squash(item["quote"])):
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


def v20(f, rec):
    """지침 제3조②: a software business (소프트웨어 진흥법 제2조 2·3호, bundled orders included — 지침 제2조②)
    states in 공고문 or 제안요청서 whether the large-company floor applies. A document only referred to is not
    input (S7-10), so it cannot supply the statement. Requiring 소프트웨어사업자 registration (제2조 4호) is the
    notice itself treating the order as software business."""
    software = fv.quoted(f.get("sw_project_quote"), rec) or fv.quoted(f.get("sw_provider_quote"), rec)
    return int(software and not fv.quoted(f.get("sw_floor_statement_quote"), rec))


VERDICTS = {"v1": v1, "v20": v20}
# Items judged on the documents present even when some are missing: S7-10 makes a document only referred to
# not input, so v20's missing statement stays missing.
JUDGED_WHEN_INCOMPLETE = {"v20"}
SCHEMA = {
    "v1_limits": [{"quote": str, "kind": str, "private_firms_allowed": bool, "statute_quote": TEXT,
                   "need_quote": TEXT, "special_quote": TEXT}],
    "sw_project_quote": TEXT, "sw_provider_quote": TEXT, "sw_floor_statement_quote": TEXT,
    "sw_referenced_missing": bool, "정보부족": bool,
}
KEYS = [*SCHEMA, "정보부족_사유"]


def label(item, f, rec):
    if f.get("정보부족") is True and item not in JUDGED_WHEN_INCOMPLETE:
        return 0
    return VERDICTS[item](f, rec)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--facts", required=True)
    args = parser.parse_args(argv)
    facts = {}
    for line in Path(args.facts).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            facts[row["id"]] = row["facts"]
    failed = sorted(i for i, f in facts.items() if harness.shape_errors(f, SCHEMA))
    facts = {i: f for i, f in facts.items() if i not in failed}
    recs = {r["id"]: r for r in fv.script.iter_records(str(ROOT / "open/dev.jsonl")) if r["id"] in facts}
    with (ROOT / "open/dev_labels.csv").open(encoding="utf-8") as stream:
        truth = {r["id"]: r for r in csv.DictReader(stream)}
    print(f"notices {len(facts)} · 형식 실패 {len(failed)} {failed}")
    for item in VERDICTS:
        pairs = [(label(item, f, recs[i]), int(truth[i][item])) for i, f in facts.items()]
        tp = sum(y and t for y, t in pairs)
        fp = sum(y and not t for y, t in pairs)
        fn = sum(t and not y for y, t in pairs)
        f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else float("nan")
        print(f"{item:4} {tp:3} {fp:3} {fn:3}  {f1:.3f}  {harness.grade(f1)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
