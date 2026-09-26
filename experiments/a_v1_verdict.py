"""labels-600 v1 labeler — one question for v1 alone, decided by code, majority over repeated runs.

Question: reports/labels-600/facts/question-v1.md. Revised on all of dev 200, so its dev score is fitted.
The labeler's answers swing between runs on the same notice by about as much as a question edit moves the score
(docs/tasks/labels-600.md), so each notice takes the majority of an odd number of runs.

    python -X utf8 experiments/a_v1_verdict.py --facts run1.jsonl [run2.jsonl run3.jsonl]
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
import a_focus_verdict as focus  # noqa: E402

fv, harness = focus.fv, focus.harness
SCHEMA = {
    "v1_limits": [{"quote": str, "kind": str, "private_firms_allowed": bool, "statute_quote": fv.TEXT,
                   "need_quote": fv.TEXT, "use_quote": fv.TEXT}],
    "정보부족": bool,
}
KEYS = [*SCHEMA, "정보부족_사유"]
# 국가계약법 시행령 제26조①5호가목5)·7) name the counterparties a 수의계약 may be made with; limiting a 수의계약
# to one of them is the decree's own ground, not an added qualification.
DECREE_COUNTERPARTY = re.compile(r"여성기업|장애인기업|사회적기업|사회적협동조합|자활기업|청년창업기업")
# A limit by where the bidder keeps its office is v5–v7's.
JURISDICTION = re.compile(r"관내")
# 영 제12조① 2호: a 신고·등록·허가·면허 another law requires is a qualification, also when named as a firm type.
REGISTERED_TYPE = re.compile(r"신고|등록|허가|면허")
# S7-5 scopes v1 to a specific facility or a holding "일정 규모 이상". A holding the requirement itself states is
# for supplying or carrying out this contract, with no number, size or coverage, is the contract's own means.
STATED_PURPOSE = re.compile(r"필요한|위한")
# "일정 규모 이상" is a count of two or more units, people or sites, or a coverage. Insurance amounts, temperatures,
# tonnage or seats of one vehicle and a single unit are not a scale.
SCALE = re.compile(r"(?<![\d.])(?:[2-9]|\d{2,})\s*(?:대|명|인(?!승)|개소|곳|개|기)(?:\s*이상)?|모든|전국|각\s*(?:시|도|광역)")
BIDDER = re.compile(r"업체|사업자|회사|법인|기관|입찰자|참가자|(?:한|된|춘|있는|없는|갖춘)\s*자(?![격재료원])")
# A holding the bidder may meet by leasing (임차) limits no one but those without the contract's own means.
LEASABLE = re.compile(r"임차")
# A holding a cited law's registration or permit itself entails (영 제12조① 2호).
LAW_REGISTRATION = re.compile(r"(?:법|법률|시행령|시행규칙)[」｣』\s]*(?:제\s*\d+\s*조)?[^。]{0,60}?(?:등록|허가|면허)"
                              r"|(?:등록|허가|면허)[^。]{0,40}?(?:법|법률)[」｣』]")


def v1(f, rec):
    """국가·지방 시행규칙 제17조: nothing beyond 영 제12조/제13조 without a legal basis (S7-5). A concrete
    holding stands where the task documents show that holding is what the task is performed with — relevance
    alone does not clear it under 제한경쟁, and 소액수의 is not exempt as a class (S7-12). A 지방 소액수의 견적 may
    limit by staff or equipment the contract needs (집행기준 제5장 1.6) 라·마), and the stated use in the task
    documents clears it (S7-7). Judged on the documents present (S7-10): a limit written in the notice is not
    undone by a missing attachment."""
    law, method = focus.contract(rec)
    negotiated = method.startswith("수의")
    small_quote = law == "지방계약법" and negotiated
    for item in f.get("v1_limits") or []:
        if not isinstance(item, dict) or not fv.quoted(item.get("quote"), rec):
            continue
        quote = fv.squash(item["quote"])
        if focus.OTHER_ITEM_LIMIT.search(quote) or JURISDICTION.search(quote) \
                or fv.quoted(item.get("statute_quote"), rec):
            continue
        if negotiated and DECREE_COUNTERPARTY.search(quote):
            continue
        if item.get("kind") in ("institution_type", "named_organisation"):
            if item.get("private_firms_allowed") is False and not REGISTERED_TYPE.search(quote):
                return 1
        elif item.get("kind") == "facility_equipment_staff":
            # A participation requirement decides who may bid, so it names the bidder; an equipment list line
            # ("- 차량용 소화기 1대") is not one.
            if not BIDDER.search(quote) or fv.quoted(item.get("need_quote"), rec):
                continue
            if not SCALE.search(quote) and (STATED_PURPOSE.search(quote) or LEASABLE.search(quote)
                                            or LAW_REGISTRATION.search(quote)):
                continue
            if small_quote and fv.quoted(item.get("use_quote"), rec):
                continue
            return 1
    return 0


def majority(runs, identifier, rec):
    votes = [v1(run[identifier], rec) for run in runs if identifier in run]
    return int(sum(votes) * 2 > len(votes))


def load(path):
    rows = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if not harness.shape_errors(row["facts"], SCHEMA):
                rows[row["id"]] = row["facts"]
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--facts", nargs="+", required=True)
    args = parser.parse_args(argv)
    runs = [load(path) for path in args.facts]
    ids = set().union(*runs)
    recs = {r["id"]: r for r in fv.script.iter_records(str(ROOT / "open/dev.jsonl")) if r["id"] in ids}
    with (ROOT / "open/dev_labels.csv").open(encoding="utf-8") as stream:
        truth = {r["id"]: r for r in csv.DictReader(stream)}
    for name, pick in [*((f"run{n + 1}", [run]) for n, run in enumerate(runs)), ("majority", runs)]:
        cells = [(i, majority(pick, i, recs[i]), int(truth[i]["v1"]))
                 for i in sorted(ids) if any(i in r for r in pick)]
        tp = sum(y and t for _, y, t in cells)
        fp = sum(y and not t for _, y, t in cells)
        fn = sum(t and not y for _, y, t in cells)
        f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else float("nan")
        errors = [("FP " if y else "FN ") + i for i, y, t in cells if y != t]
        pairs = cells
        print(f"{name:9} {len(pairs)} v1 {tp}/{fp}/{fn} {f1:.3f} {harness.grade(f1)} {' '.join(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
