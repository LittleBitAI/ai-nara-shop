"""C-variance — 같은 코드 N회 통과의 Macro 범위와 쌍별 갈린 셀을 낸다. 모델을 안 부른다.

이 스크립트는 회차 전에 고정됐다. 결과를 보고 고치지 않는다.

내는 것은 넷이고, 그 넷만 보고에 쓴다.

  1. 통과별 Macro 와 그 범위(min · max · 범위폭)
  2. 쌍마다 갈린 셀 수와 Macro 차이 — N개면 N(N-1)/2 쌍
  3. 항목별로 몇 번 흔들렸는지 (24항목 각각, 몇 쌍에서 갈렸나)
  4. 설정이 정말 같았는지 — code/input/records 해시와 seed·temperature 대조

표준편차는 안 낸다. N 이 작을 때 그 수는 신뢰구간이 넓어 "분포를 추정했다" 는 착각을
준다. 보고는 관측된 범위로만 한다 — `README.md` §3-3.

    py -X utf8 reports/team-c/c-variance/aggregate.py --runs <등록된 회차 폴더> ...

각 폴더는 `submission.csv` 와 `run_report.json` 을 든다.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ITEMS = [f"v{n}" for n in range(1, 25)]
# 설정이 같아야 변동폭이라 부를 수 있다. 하나라도 갈리면 그것은 설정 차이다.
PINNED = ("code_sha256", "input_sha256", "records_sha256", "seed", "temperature",
          "thinking", "prompt_budget", "max_tokens", "max_chars")


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return {row["id"]: row for row in csv.DictReader(stream)}


def score(rows, truth):
    """항목별 TP/FP/FN 과 24항목 F1 평균. tools/score.py 와 같은 정의다."""
    items, total = {}, 0.0
    for item in ITEMS:
        tp = fp = fn = 0
        for key, row in rows.items():
            label, pred = truth[key][item], row[item]
            tp += label == pred == "1"
            fp += label == "0" and pred == "1"
            fn += label == "1" and pred == "0"
        f1 = 0.0 if not tp else 2 * tp / (2 * tp + fp + fn)
        items[item] = {"tp": tp, "fp": fp, "fn": fn, "f1": f1}
        total += f1
    return total / len(ITEMS), items


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", nargs="+", required=True,
                        help="통과 폴더들. 각각 submission.csv 와 run_report.json 을 든다")
    parser.add_argument("--truth", default=str(ROOT / "open/dev_labels.csv"))
    parser.add_argument("--output", help="요약 JSON 을 쓸 경로")
    args = parser.parse_args(argv)

    with open(args.truth, encoding="utf-8", newline="") as stream:
        truth = {row["id"]: row for row in csv.DictReader(stream)}

    runs = []
    for folder in args.runs:
        path = Path(folder)
        rows = read_rows(path / "submission.csv")
        report = json.loads((path / "run_report.json").read_text(encoding="utf-8"))
        macro, items = score(rows, truth)
        runs.append({"name": path.name, "rows": rows, "report": report,
                     "macro": macro, "items": items})

    # 4. 설정 대조가 먼저다. 갈리면 나머지 수를 변동폭이라 부를 수 없다.
    print("=== 설정 대조 — 이것이 같아야 변동폭이다 ===")
    settings_ok = True
    for key in PINNED:
        values = {r["report"].get(key) for r in runs}
        if len(values) != 1:
            settings_ok = False
        shown = str(next(iter(values)))[:34] if len(values) == 1 else f"{len(values)}가지로 갈림"
        print(f"  {key:<18}{shown:<38}{'같다' if len(values) == 1 else '**다르다**'}")
    debug = {r["report"]["reproduction"]["settings"].get("debug_responses") for r in runs}
    if len(debug) != 1:
        settings_ok = False
    print(f"  {'debug_responses':<18}{str(next(iter(debug))) if len(debug) == 1 else '갈림':<38}"
          f"{'같다' if len(debug) == 1 else '**다르다**'}")
    if not settings_ok:
        print("\n설정이 갈렸다. 이 수를 변동폭으로 쓰지 않는다 — 설정 차이다.")

    # 1. 통과별 Macro 와 범위
    print(f"\n=== 통과 {len(runs)}회의 Macro ===")
    width = max(len(r["name"]) for r in runs) + 2
    for run in sorted(runs, key=lambda r: r["macro"]):
        print(f"  {run['name']:<{width}}{run['macro']:.12f}")
    low = min(r["macro"] for r in runs)
    high = max(r["macro"] for r in runs)
    print(f"\n  최소 {low:.12f}")
    print(f"  최대 {high:.12f}")
    print(f"  범위 {high - low:.12f}   ← 관측 {len(runs)}회의 범위다. 분포가 아니다")

    # 2. 쌍별 갈린 셀과 Macro 차이
    print(f"\n=== 쌍 {len(runs) * (len(runs) - 1) // 2}개 ===")
    pairs = []
    for one, two in itertools.combinations(runs, 2):
        changed = [(i, it) for i in one["rows"] for it in ITEMS
                   if one["rows"][i][it] != two["rows"][i][it]]
        gap = abs(one["macro"] - two["macro"])
        pairs.append({"a": one["name"], "b": two["name"],
                      "cells": len(changed), "macro_gap": gap})
    for pair in sorted(pairs, key=lambda p: -p["macro_gap"]):
        print(f"  {pair['a']} ↔ {pair['b']:<12}{pair['cells']:>4}셀   Macro 차 {pair['macro_gap']:.12f}")
    print(f"\n  갈린 셀 {min(p['cells'] for p in pairs)}~{max(p['cells'] for p in pairs)}")
    print(f"  Macro 차 {min(p['macro_gap'] for p in pairs):.12f}"
          f"~{max(p['macro_gap'] for p in pairs):.12f}")

    # 3. 항목별로 몇 쌍에서 흔들렸나
    print("\n=== 항목별 흔들림 (몇 쌍에서 갈렸나 · 그 쌍들의 셀 합) ===")
    shaken = {}
    for one, two in itertools.combinations(runs, 2):
        for item in ITEMS:
            count = sum(1 for i in one["rows"] if one["rows"][i][item] != two["rows"][i][item])
            if count:
                entry = shaken.setdefault(item, {"pairs": 0, "cells": 0})
                entry["pairs"] += 1
                entry["cells"] += count
    for item in ITEMS:
        entry = shaken.get(item)
        if entry:
            spread = [r["items"][item]["f1"] for r in runs]
            print(f"  {item:<5}{entry['pairs']:>3}쌍  셀 합 {entry['cells']:>4}   "
                  f"F1 {min(spread):.6f}~{max(spread):.6f}")
    quiet = [i for i in ITEMS if i not in shaken]
    print(f"  한 쌍에서도 안 갈린 항목: {quiet or '없음'}")

    if args.output:
        payload = {
            "runs": [{"name": r["name"], "macro": r["macro"],
                      "items": r["items"]} for r in runs],
            "macro_min": low, "macro_max": high, "macro_range": high - low,
            "pairs": pairs,
            "cells_min": min(p["cells"] for p in pairs),
            "cells_max": max(p["cells"] for p in pairs),
            "shaken_items": shaken,
            "settings_identical": settings_ok,
            "note": "관측 범위다. 분포·표준편차가 아니다.",
        }
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=1)
            stream.write("\n")
        print(f"\n요약을 {out} 에 썼다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
