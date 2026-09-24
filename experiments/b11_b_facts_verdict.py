"""B11 — labeler facts → item verdicts in code, scored against human dev labels.

One verdict function per item in VERDICTS. Adding an item to the dataset later means adding a
schema section to the question file and one function here. The mapping was fixed in
docs/tasks/b-facts-labeler.md before any run; do not tune it on dev results.

    python -X utf8 experiments/b11_b_facts_verdict.py --facts <facts.jsonl> [--model-csv <HEAD dev replay>]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import script  # noqa: E402

ROUND_WON = 1_000           # display rounding; B9 measured 2~1,000 won gaps as the same money


def v9(f, rec):
    return int(f.get("v9_role") in ("deliverable", "deliverable_or_equivalent"))


def v19(f, rec):
    return int(f.get("v19_pledge") == "yes" and f.get("v19_timing") == "by_bid")


def v21(f, rec):
    share = f.get("v21_min_share_percent")
    if f.get("v21_joint_contract") == "barred" or f.get("v21_method") == "분담이행" \
            or not isinstance(share, (int, float)) or isinstance(share, bool):
        return 0
    floor = script.v21_minimum_share(rec)
    return int(floor is not None and share < floor)


def v24(f, rec):
    meta = rec.get("meta") or {}
    method = f.get("v24_contract_method")
    if method not in (None, "not_stated") and meta.get("계약방법") and method != meta.get("계약방법"):
        return 1
    text_limited = f.get("v24_region_restricted") == "yes"
    meta_limited = meta.get("지역제한여부") == "Y"
    if text_limited != meta_limited:
        return 1
    listed = str(meta.get("제한지역코드목록") or "")
    regions = [r for r in f.get("v24_regions") or [] if isinstance(r, str)]
    if text_limited and meta_limited and listed and "[" not in listed and regions \
            and not any("[" in r for r in regions):
        if script._region_key(regions) != script._region_key(script._region_names(listed)):
            return 1
    registered = set(script.META_INDUSTRY.findall(str(meta.get("면허업종제한목록") or "")))
    if any(str(code) not in registered for code in f.get("v24_industry_codes") or []):
        return 1
    fields = (("추정가격", "입찰추정가격"), ("배정예산", "배정예산금액"), ("사업예산", "배정예산금액"))
    for amount in f.get("v24_amounts") or []:
        if not isinstance(amount, dict):
            continue
        label, won = str(amount.get("label") or ""), amount.get("won")
        for word, field in fields:
            registered_won = script._int(meta.get(field))
            if word in label.replace(" ", "") and isinstance(won, int) and registered_won is not None:
                if abs(won - registered_won) > ROUND_WON:
                    return 1
    return 0


VERDICTS = {"v9": v9, "v19": v19, "v21": v21, "v24": v24}


def wilson_lower(k, n, z=1.96):
    if n == 0:
        return float("nan")
    p, d = k / n, 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def grade(f1):
    return "신뢰" if f1 >= 0.80 else "조건부" if f1 >= 0.60 else "제외"


def main(argv=None, verdicts=None):
    verdicts = verdicts or VERDICTS
    parser = argparse.ArgumentParser()
    parser.add_argument("--facts", required=True)
    parser.add_argument("--model-csv", help="HEAD dev replay CSV; adds the model-TP-cell hit column")
    args = parser.parse_args(argv)
    facts = {}
    for line in Path(args.facts).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            facts[row["id"]] = row["facts"]
    recs = {r["id"]: r for r in script.iter_records(str(ROOT / "open/dev.jsonl"), None) if r["id"] in facts}
    with (ROOT / "open/dev_labels.csv").open(encoding="utf-8") as stream:
        truth = {r["id"]: r for r in csv.DictReader(stream)}
    model = {}
    if args.model_csv:
        with open(args.model_csv, encoding="utf-8") as stream:
            model = {r["id"]: r for r in csv.DictReader(stream)}
    print(f"notices {len(facts)} · 정보부족 {sum(bool(f.get('정보부족')) for f in facts.values())}")
    print("item  TP  FP  FN  labeler-F1  model-TP-hit  Wilson-lower  grade")
    for item, verdict in verdicts.items():
        tp = fp = fn = 0
        cells = hits = 0
        for i, f in facts.items():
            y, t = verdict(f, recs[i]), int(truth[i][item])
            tp += y and t
            fp += y and not t
            fn += t and not y
            if model and t and int(model[i][item]):
                cells += 1
                hits += y
        f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else float("nan")
        hit = f"{hits}/{cells}" if model else "-"
        low = f"{wilson_lower(hits, cells):.3f}" if model and cells else "-"
        print(f"{item:4} {tp:3} {fp:3} {fn:3}  {f1:10.3f}  {hit:>12}  {low:>12}  {grade(f1)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
