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

설정이 하나라도 갈리면 범위를 내기 전에 exit 2 로 멈춘다. 설정이 갈린 쌍(`dev` ·
`dev-debug`)을 일부러 보려면 `--allow-mismatch` 를 준다 — 그때도 수는 내지만 exit 1 이다.
exit 0 은 같은 설정의 변동폭일 때만 나온다.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ITEMS = [f"v{n}" for n in range(1, 25)]


def _hex(n):
    return lambda v: isinstance(v, str) and re.fullmatch(f"[0-9a-f]{{{n}}}", v) is not None


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _bool(v):
    return isinstance(v, bool)


def _text(v):
    return isinstance(v, str) and v.strip() != ""


# 설정이 같아야 변동폭이라 부를 수 있다. 각 설정은 **잎 값 하나**이고 형식이 맞아야 한다.
# 없거나 null 이거나 형식이 틀리면 확인하지 못한 것이다 — 모든 통과가 똑같이 비어 있어도
# 같은 게 아니다. 객체를 통째로 비교하지 않는다. 빠진 하위 키끼리 같아 보이기 때문이다.
# 모델과 실행 환경도 넣는다. 변동폭은 같은 모델·같은 엔진에서만 변동폭이다.
SETTINGS = {
    "code_sha256": (("code_sha256",), _hex(64)),
    "input_sha256": (("input_sha256",), _hex(64)),
    "records_sha256": (("records_sha256",), _hex(64)),
    "seed": (("seed",), _int),
    "temperature": (("temperature",), _number),
    "thinking": (("thinking",), _bool),
    "prompt_budget": (("prompt_budget",), _int),
    "max_tokens": (("max_tokens",), _int),
    "max_chars": (("max_chars",), _int),
    "model.id": (("model", "id"), _text),
    "model.revision": (("model", "expected_revision"), _hex(40)),
    "vllm": (("environment", "vllm"), _text),
    "cuda": (("environment", "cuda"), _text),
    "chat_template_sha256": (("environment", "chat_template_sha256"), _hex(64)),
    "sampling_params": (("environment", "sampling_params"), _text),
    "model_dir": (("reproduction", "settings", "model_dir"), _text),  # 받은 리비전 경로
    "debug_responses": (("reproduction", "settings", "debug_responses"), _bool),
}
MISSING = object()


def dig(report, path):
    """중첩 키를 따라간다. 없으면 `MISSING`."""
    node = report
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return MISSING
        node = node[key]
    return node


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
    parser.add_argument("--allow-mismatch", action="store_true",
                        help="설정이 갈려도 수를 낸다. 변동폭이 아니므로 exit 1 로 끝난다")
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
    for label, (path, valid) in SETTINGS.items():
        values = [dig(r["report"], path) for r in runs]
        invalid = sum(value is MISSING or not valid(value) for value in values)
        distinct = {json.dumps(value) for value in values if value is not MISSING}
        if invalid:
            shown, verdict = f"{invalid}개 통과에 없거나 형식 틀림", "**확인 불가**"
        elif len(distinct) != 1:
            shown, verdict = f"{len(distinct)}가지로 갈림", "**다르다**"
        else:
            shown, verdict = str(values[0])[:34], "같다"
        settings_ok = settings_ok and verdict == "같다"
        print(f"  {label:<22}{shown:<38}{verdict}")
    if not settings_ok:
        print("\n설정이 갈렸거나 확인할 수 없다. 이 수를 변동폭으로 쓰지 않는다.")
        if not args.allow_mismatch:
            print("범위를 내지 않고 멈춘다. 설정 차이를 일부러 보려면 --allow-mismatch.")
            return 2

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
    return 0 if settings_ok else 1


if __name__ == "__main__":
    sys.exit(main())
