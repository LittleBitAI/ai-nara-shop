"""v10·v11·v13 의 오류 셀을 여섯 통과 위에서 센다. 모델을 안 부른다.

`README.md` 의 §1~§3 과 §5 를 내는 스크립트다. 내는 것은 넷이다.

  1. 항목별 TP/FP/FN 을 통과마다 — 여섯이 같은지가 이 회차의 값이다
  2. 오류 셀을 공고 단위로, 몇 통과가 1 을 냈는지와 함께
     (0/6 이나 6/6 이면 고정, 그 사이면 흔들림)
  3. 단계별 대조 — baseline · company_size_baseline · submission 중
     어디서 값이 생겼나. 규칙이 만든 오류와 모델이 만든 오류를 가른다
  4. 오류 묶음을 닫았을 때의 Macro 상한

    py -X utf8 reports/team-c/v10-v11-v13-breakdown/breakdown.py [--run <회차 폴더>]
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "reports/runs/colab-1790445336782946136"
PASSES = [f"var-{k:02d}" for k in range(1, 7)]
FOCUS = ("v10", "v11", "v13")
STAGES = (("base", "baseline_submission.csv"),
          ("cs", "company_size_baseline_submission.csv"),
          ("final", "submission.csv"))


def read(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return {row["id"]: row for row in csv.DictReader(stream)}


def f1(tp, fp, fn):
    return 0.0 if not tp else 2 * tp / (2 * tp + fp + fn)


def counts(rows, truth, item):
    tp = fp = fn = 0
    for key, row in rows.items():
        label, pred = truth[key][item], row[item]
        tp += label == pred == "1"
        fp += label == "0" and pred == "1"
        fn += label == "1" and pred == "0"
    return tp, fp, fn


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", default=str(RUN), help="회차 폴더 (var-01 … var-06 을 든다)")
    parser.add_argument("--truth", default=str(ROOT / "open/dev_labels.csv"))
    args = parser.parse_args(argv)

    run = Path(args.run)
    truth = read(Path(args.truth))
    stages = {name: {key: read(run / name / filename) for key, filename in STAGES}
              for name in PASSES}
    final = {name: stages[name]["final"] for name in PASSES}

    # 1. 통과별 TP/FP/FN
    print("=== 통과별 TP/FP/FN — 여섯이 같은지를 먼저 본다 ===")
    base_counts = {}
    for item in FOCUS:
        positives = sum(truth[key][item] == "1" for key in truth)
        seen = {counts(final[name], truth, item) for name in PASSES}
        print(f"\n  {item}  정답 양성 {positives}건")
        for name in PASSES:
            tp, fp, fn = counts(final[name], truth, item)
            print(f"    {name}  TP {tp}  FP {fp}  FN {fn}  F1 {f1(tp, fp, fn):.6f}")
        print(f"    → {'여섯 통과가 같다' if len(seen) == 1 else f'{len(seen)}가지로 갈린다'}")
        # 상한은 **최빈 통과**를 기준으로 낸다. 여섯이 같으면 그 값이고, 갈리면 다수 쪽이다 —
        # `var-01` 을 기준으로 삼으면 v13 처럼 한 통과만 다른 항목에서 소수 쪽을 집는다.
        tally = Counter(counts(final[name], truth, item) for name in PASSES)
        base_counts[item], seats = tally.most_common(1)[0]
        if len(tally) > 1:
            print(f"    → 상한은 최빈 {seats}/{len(PASSES)} 통과의 "
                  f"TP{base_counts[item][0]} FP{base_counts[item][1]} FN{base_counts[item][2]} 기준")

    # 2. 오류 셀과 그 안정성
    print("\n=== 오류 셀 — 1 로 낸 통과 수 (0/6·6/6 이면 고정) ===")
    unstable = []
    for item in FOCUS:
        print(f"\n  {item}")
        for key in final[PASSES[0]]:
            label = truth[key][item]
            hits = sum(final[name][key][item] == "1" for name in PASSES)
            if label == "1" and hits == len(PASSES):
                continue
            if label == "0" and hits == 0:
                continue
            kind = "FN" if label == "1" else "FP"
            mark = "  ← 흔들림" if 0 < hits < len(PASSES) else ""
            if mark:
                unstable.append((item, key))
            print(f"    {kind}  {key:14} 정답 {label}  1 로 낸 통과 {hits}/{len(PASSES)}{mark}")
    print(f"\n  흔들리는 셀: {unstable or '없음'}")

    # 3. 단계별 — 누가 만든 오류인가
    print("\n=== 단계별 대조 — 값이 어디서 생기나 ===")
    print(f"  {'항목':5}{'공고':16}{'정답':5}{'base':14}{'cs':14}{'final':14}")
    for item in FOCUS:
        for key in final[PASSES[0]]:
            label = truth[key][item]
            hits = sum(final[name][key][item] == "1" for name in PASSES)
            if (label == "1" and hits == len(PASSES)) or (label == "0" and hits == 0):
                continue

            def column(stage):
                values = [stages[name][stage][key][item] for name in PASSES]
                return values[0] if len(set(values)) == 1 else "/".join(values)

            print(f"  {item:5}{key:16}{label:^5}"
                  f"{column('base'):14}{column('cs'):14}{column('final'):14}")

    # 4. 상한
    print("\n=== 상한 — 이 오류를 닫으면 Macro 가 얼마 오르나 (항목 F1 ÷ 24) ===")
    for item in FOCUS:
        tp, fp, fn = base_counts[item]
        now = f1(tp, fp, fn)
        for label, after in ((f"{item} FP 전부", (tp, 0, fn)),
                             (f"{item} FN 전부", (tp + fn, fp, 0)),
                             (f"{item} 완전", (tp + fn, 0, 0))):
            gain = f1(*after) - now
            print(f"  {label:18} F1 {now:.6f} → {f1(*after):.6f}   Macro {gain / 24:+.6f}")
    print("\n  주의 — `PPS-DEV-193` v13 은 운영진이 인정한 dev 라벨 노이즈다"
          "(`docs/qna.md`). 위 'v13 FP 전부' 는 그 셀을 포함하므로 실제로 쫓을 수 있는"
          " 상한이 아니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
