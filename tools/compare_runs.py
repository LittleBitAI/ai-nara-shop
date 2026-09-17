"""두 실행의 예측 CSV를 항목별로 대조한다. 모델 미사용이며 점수를 다시 매기지 않는다."""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
# 회차 간 churn의 실측 범위. 여덟 쌍에서 관측했고 reports/runs/reproducibility.md가 소유한다.
# 셀 수로는 구분되지 않는다 — 30셀이 0.0026을 내고 41셀이 0.000008을 냈다.
# 같은 코드가 dev Macro F1 0.2182를 세 번, 0.2208을 한 번 냈다.
DRIFT_MIN = 0.000007917373
DRIFT_MAX = 0.003128882280
DRIFT_CELLS = (25, 43)
DRIFT_PAIRS = 8


def load_score():
    spec = importlib.util.spec_from_file_location("score_tool", ROOT / "tools/score.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compare(score, truth_path, before_path, after_path, focus=()):
    truth, _ = score.load_csv(Path(truth_path))
    before, _ = score.load_csv(Path(before_path))
    after, _ = score.load_csv(Path(after_path))
    if before.keys() != after.keys():
        raise ValueError("두 예측의 ID 집합이 다르다. 같은 입력의 회차끼리만 대조한다")
    unknown = [item for item in focus if item not in score.ITEMS]
    if unknown:
        raise ValueError(f"항목 이름이 아니다: {unknown}")
    metrics_before, _ = score.calculate(truth, before)
    metrics_after, _ = score.calculate(truth, after)

    items = []
    for index, name in enumerate(score.ITEMS):
        flipped = sorted(i for i in before if before[i][index] != after[i][index])
        mb, ma = metrics_before["items"][name], metrics_after["items"][name]
        items.append({
            "item": name, "focus": name in focus, "flipped": flipped,
            "before": {k: mb[k] for k in ("tp", "fp", "fn", "f1")},
            "after": {k: ma[k] for k in ("tp", "fp", "fn", "f1")},
            "support": mb["support"],
        })
    delta = metrics_after["macro_f1"] - metrics_before["macro_f1"]
    changed = sum(len(row["flipped"]) for row in items)
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "truth": score.portable(truth_path), "before": score.portable(before_path),
        "after": score.portable(after_path), "notices": len(before),
        "focus": list(focus),
        "macro_f1": {"before": metrics_before["macro_f1"], "after": metrics_after["macro_f1"],
                     "delta": delta},
        "changed_cells": changed,
        "changed_cells_off_focus": sum(len(r["flipped"]) for r in items if not r["focus"]),
        # churn은 임계값이 아니다. 관측 범위만 적고 판정은 사람이 한다.
        "drift_reference": {
            "macro_f1_min": DRIFT_MIN, "macro_f1_max": DRIFT_MAX, "cells": list(DRIFT_CELLS),
            "pairs": DRIFT_PAIRS, "below_observed_max": abs(delta) <= DRIFT_MAX,
            "source": "reports/runs/reproducibility.md"},
        "items": items,
    }


def render(result, show_all=False):
    lines = [
        f"기준 {result['before']}",
        f"후보 {result['after']}",
        f"정답 {result['truth']} · 공고 {result['notices']}건"
        + (f" · 대상 {', '.join(result['focus'])}" if result["focus"] else ""),
        "",
        f"Macro F1  {result['macro_f1']['before']:.12f} → {result['macro_f1']['after']:.12f}"
        f"  ({result['macro_f1']['delta']:+.12f})",
        f"바뀐 셀   {result['changed_cells']} / {result['notices'] * 24}"
        f"   (대상 밖 {result['changed_cells_off_focus']})",
        "",
    ]
    lines += [
        f"churn    회차 간 실측 {DRIFT_CELLS[0]}~{DRIFT_CELLS[1]}셀, 그 Macro F1 영향"
        f" {DRIFT_MIN:.6f}~{DRIFT_MAX:.6f} ({DRIFT_PAIRS}쌍)",
    ]
    if result["drift_reference"]["below_observed_max"]:
        lines += ["         이번 차이는 그 범위 안이다. Macro F1만으로는 아무것도 말할 수 없다.",
                  "         대상 항목의 TP/FP/FN이 가설대로 움직였는지로 판단한다."]
    else:
        lines += ["         이번 차이는 관측 범위를 넘는다. 그래도 항목별 변화를 함께 확인한다."]
    lines += [f"         근거 {result['drift_reference']['source']}", ""]
    lines.append(f"{'항목':<5} {'TP':>9} {'FP':>9} {'FN':>9} {'F1':>21}  바뀐 공고")
    for row in result["items"]:
        if not (show_all or row["flipped"] or row["focus"]):
            continue
        b, a = row["before"], row["after"]
        mark = "*" if row["focus"] else " "
        ids = ", ".join(row["flipped"][:6]) + ("…" if len(row["flipped"]) > 6 else "")
        lines.append(
            f"{mark}{row['item']:<4} {b['tp']:>4}→{a['tp']:<4} {b['fp']:>4}→{a['fp']:<4} "
            f"{b['fn']:>4}→{a['fn']:<4} {b['f1']:>9.6f}→{a['f1']:<9.6f} "
            f"{len(row['flipped']):>3}  {ids}")
    lines += ["", "* = --items로 지정한 대상 항목. 대상 밖 변화는 회귀 후보다.",
              "이 대조는 두 CSV만 본다. 실행 환경·시간·모델 호출 성공은 각 실행의 manifest.json이 소유한다."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")  # 파이프에 붙은 파이썬은 로케일 인코딩으로 죽는다.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, help="기준 실행의 예측 CSV")
    parser.add_argument("--after", required=True, help="후보 실행의 예측 CSV")
    parser.add_argument("--truth", default=str(ROOT / "open/dev_labels.csv"))
    parser.add_argument("--items", default="", help="쉼표로 구분한 대상 항목, 예: v8,v16")
    parser.add_argument("--all", action="store_true", help="변화 없는 항목도 모두 출력")
    parser.add_argument("--output-dir", type=Path, help="새 디렉터리. 기존 경로는 거부한다")
    args = parser.parse_args(argv)
    try:
        if args.output_dir and args.output_dir.exists():
            raise ValueError(f"{args.output_dir} 가 이미 있다. 새 경로를 쓴다")
        result = compare(load_score(), args.truth, args.before, args.after,
                         tuple(x.strip() for x in args.items.split(",") if x.strip()))
        report = render(result, args.all)
        if args.output_dir:
            args.output_dir.mkdir(parents=True)
            (args.output_dir / "comparison.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                encoding="utf-8", newline="\n")
            (args.output_dir / "comparison.md").write_text(
                "# 회차 대조\n\n```text\n" + report + "```\n", encoding="utf-8", newline="\n")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
