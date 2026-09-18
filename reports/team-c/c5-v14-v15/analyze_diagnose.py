"""진단 회차의 `items.jsonl` 을 항목별 TP/FP/FN 과 막힌 단계로 정리한다.

회차가 오면 손으로 세지 않기 위해 **미리** 만들어 둔다. 어느 회차·어느 항목에도 돌아가며,
기존 회차로 검증할 수 있다. 모델을 부르지 않는다.

C5 용으로 쓸 때 보는 것은 셋이다.
1. v14·v15 의 TP/FP/FN — 이 항목을 별도로 물어본 적이 한 번도 없다.
2. **FN 이 어느 단계에서 막혔나** — `context_not_observed` 면 문맥을 못 봤고,
   `condition_not_met` 면 봤는데 조건을 잘못 맞췄다. 처방이 갈린다.
3. 조건표의 금액 구간을 덧씌우면 무엇이 달라지나 — **진단이지 채택이 아니다.**
   구간은 양성을 지우는 방향으로만 작동하므로 FN 을 고치지 못한다.

실행:
    py -X utf8 reports/team-c/c5-v14-v15/analyze_diagnose.py <items.jsonl> [--items v14,v15]
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEV = REPO / "open/dev.jsonl"

# 금액 읽기와 구간은 후보에서 가져온다. 복제본을 두지 않는다.
sys.path.insert(0, str(REPO))
from experiments.sme_candidate import NOTICE_AMOUNT_WON, SME_BAND_FLOOR_WON, estimated_price  # noqa: E402

STAGES = ("context_not_observed", "fact_not_extracted", "condition_not_met", "violation_found")

# C5 조건표의 구간. 근거는 같은 폴더의 README.md 가 조문 위치와 함께 적는다.
# **진단용 오버레이다.** 후보에 심은 게이트가 아니다.
BANDS = {
    "v14": (NOTICE_AMOUNT_WON, None),          # 고시금액 이상
    "v15": (SME_BAND_FLOOR_WON, NOTICE_AMOUNT_WON),  # 1억 이상 - 고시금액 미만
    "v16": (SME_BAND_FLOOR_WON, NOTICE_AMOUNT_WON),
    "v18": (None, SME_BAND_FLOOR_WON),
}


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def in_band(item: str, amount: int | None) -> bool:
    """금액을 못 읽으면 거르지 않는다. 결손은 음성 근거가 아니다."""
    band = BANDS.get(item)
    if band is None or amount is None:
        return True
    low, high = band
    return (low is None or amount >= low) and (high is None or amount < high)


def counts(pairs: list[tuple[int, int]]) -> dict:
    tp = sum(1 for p, t in pairs if p and t)
    fp = sum(1 for p, t in pairs if p and not t)
    fn = sum(1 for p, t in pairs if not p and t)
    denom = 2 * tp + fp + fn
    return {"tp": tp, "fp": fp, "fn": fn, "f1": (2 * tp / denom) if denom else 0.0}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("items_jsonl", help="진단 회차의 diagnose/items.jsonl")
    parser.add_argument("--items", default="", help="쉼표로 구분. 비우면 파일에 있는 전부")
    args = parser.parse_args(argv)

    path = Path(args.items_jsonl)
    if not path.is_file():
        print(f"error: {path} 가 없다", file=sys.stderr)
        return 1
    rows = load_jsonl(path)
    if not rows:
        print("error: 빈 파일이다", file=sys.stderr)
        return 1
    if rows[0].get("truth") is None:
        print("error: truth 가 없다. --labels 를 준 회차가 필요하다", file=sys.stderr)
        return 1

    present = list((rows[0].get("items") or {}).keys())
    items = [x.strip() for x in args.items.split(",") if x.strip()] or present
    unknown = [i for i in items if i not in present]
    if unknown:
        print(f"error: 회차에 없는 항목 {unknown}. 있는 것은 {present}", file=sys.stderr)
        return 1

    amounts = {r["id"]: estimated_price(r) for r in load_jsonl(DEV)}
    missing = sorted(i for i in (r["id"] for r in rows) if amounts.get(i) is None)

    print(f"회차 파일 {path.as_posix()} · 공고 {len(rows)}건 · 금액 미확인 {len(missing)}건")

    for item in items:
        plain: list[tuple[int, int]] = []
        banded: list[tuple[int, int]] = []
        stages: collections.Counter = collections.Counter()
        fn_stages: collections.Counter = collections.Counter()
        fn_ids: list[str] = []
        band_killed_tp: list[str] = []

        disagree = 0
        for row in rows:
            cell = (row.get("items") or {}).get(item) or {}
            stage = cell.get("막힌_단계")
            from_stage = 1 if stage == "violation_found" else 0
            # `판정` 이 있으면 그것을 쓴다. 지금 도구는 `막힌_단계` 에서 파생하므로 둘이 같지만,
            # 옛 회차는 모델이 두 칸을 따로 채워 어긋난다. 조용히 한쪽을 고르지 않고 세어 보여 준다.
            pred = 1 if cell.get("판정") == 1 else (0 if "판정" in cell else from_stage)
            disagree += pred != from_stage
            truth = 1 if (row.get("truth") or {}).get(item) == 1 else 0
            stages[stage] += 1
            gated = pred if (pred == 0 or in_band(item, amounts.get(row["id"]))) else 0
            plain.append((pred, truth))
            banded.append((gated, truth))
            if truth and not pred:
                fn_stages[stage] += 1
                fn_ids.append(row["id"])
            if pred and not gated and truth:
                band_killed_tp.append(row["id"])

        a, b = counts(plain), counts(banded)
        support = a["tp"] + a["fn"]
        print(f"\n### {item} · 지지 {support}건")
        print(f"  별도 질의 그대로   TP/FP/FN {a['tp']}/{a['fp']}/{a['fn']} · F1 {a['f1']:.3f}")
        if item in BANDS:
            low, high = BANDS[item]
            band = f"{'' if low is None else f'{low:,} ≤ '}추정가격{'' if high is None else f' < {high:,}'}"
            print(f"  + 조건표 구간 덧씌움 TP/FP/FN {b['tp']}/{b['fp']}/{b['fn']} · F1 {b['f1']:.3f}   ({band})")
            if band_killed_tp:
                print(f"    !! 구간이 지운 TP: {', '.join(band_killed_tp)}  ← 구간이 조문과 어긋난다")
        print("  막힌 단계 전체: " + ", ".join(f"{s}={stages[s]}" for s in STAGES if stages[s]))
        if disagree:
            print(f"  !! `판정` 과 `막힌_단계` 가 {disagree}건 어긋난다 — 위 수치는 `판정` 기준이다.")
            print("     두 칸을 따로 채우던 옛 회차다. 단계 히스토그램을 근거로 쓰지 마라.")
        if fn_stages:
            print("  **놓친 양성이 막힌 단계**: "
                  + ", ".join(f"{s}={fn_stages[s]}" for s in STAGES if fn_stages[s]))
            print(f"    공고: {', '.join(fn_ids)}")

    print("\n진단이다. 제출 판정·점수가 아니며 채택 근거가 아니다.")
    print("절대 수치는 회차에 딸려 있다. 회차 이름 없이 인용하지 않는다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
