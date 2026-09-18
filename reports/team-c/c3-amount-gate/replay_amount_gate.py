"""C3 1-1 · 1-2 — 부재탐지 3항목에 금액 게이트를 씌워 다시 잰다.

`tools/diagnose_items.py` 가 회차 `colab-1789658250172468461` 에서 남긴 공고별 판정에
`open/dev.jsonl` 의 `meta.입찰추정가격` 구간을 씌운다. 모델을 부르지 않는다.

items.jsonl 에서 쓰는 칸은 `판정` 하나다. `막힌_단계` 는 쓰지 않는다 —
`판정=1` 인 370건 중 286건이 단계와 어긋난다(`reports/team-score-audit/absence-detection.md`).

한 항목에 여러 후보 구간을 같이 낸다. 인수인계의 잠정값과 제공 조문에서 확정한 값이
다르기 때문이다. 조문 위치는 같은 폴더의 README.md 가 적는다.

실행:
    py -X utf8 reports/team-c/c3-amount-gate/replay_amount_gate.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ITEMS = REPO / "reports/runs/colab-1789658250172468461/diagnose/items.jsonl"
DEV = REPO / "open/dev.jsonl"
OUT = Path(__file__).resolve().parent / "gate-result.json"

FLOOR = 100_000_000               # 국가 시행령 제21조①10호 가목/나목의 1억원 경계
NOTICE_CONFIRMED = 230_000_000    # 재정경제부장관 고시 1.가 — 물품 및 용역 2억 3천만 원
NOTICE_PROVISIONAL = 220_000_000  # 인수인계에 적힌 잠정값. 제공 조문에 근거가 없다
SW_FLOOR = 2_000_000_000          # SW 지침 별표1 의 최저 사업금액 하한 20억원

# (이름, 항목, 하한 포함, 상한 미포함, 인수인계 목표값 또는 None).
# 경계가 None 이면 그쪽 방향으로는 거르지 않는다.
GATES = [
    ("v16 · 상한 2.2억(잠정)", "v16", FLOOR, NOTICE_PROVISIONAL, (6, 36, 0, 0.250)),
    ("v16 · 상한 2.3억(조문)", "v16", FLOOR, NOTICE_CONFIRMED, None),
    ("v18 · 1억 미만", "v18", None, FLOOR, (4, 51, 3, 0.129)),
    ("v20 · 1억 이상(임시)", "v20", FLOOR, None, (3, 39, 2, 0.128)),
    ("v20 · 20억 이상(별표1)", "v20", SW_FLOOR, None, None),
]


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def to_amount(raw: object) -> int | None:
    """meta.입찰추정가격 을 정수 원 단위로 읽는다. 읽히지 않으면 None."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    text = str(raw).strip().replace(",", "")
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def score(pairs: list[tuple[int, int]]) -> dict:
    tp = sum(1 for pred, truth in pairs if pred == 1 and truth == 1)
    fp = sum(1 for pred, truth in pairs if pred == 1 and truth == 0)
    fn = sum(1 for pred, truth in pairs if pred == 0 and truth == 1)
    tn = sum(1 for pred, truth in pairs if pred == 0 and truth == 0)
    denom = 2 * tp + fp + fn
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "f1": (2 * tp / denom) if denom else 0.0}


def main() -> None:
    amounts = {
        row["id"]: to_amount((row.get("meta") or {}).get("입찰추정가격"))
        for row in load_jsonl(DEV)
    }
    rows = load_jsonl(ITEMS)

    missing_amount = sorted(rid for rid in (r["id"] for r in rows) if amounts.get(rid) is None)
    report: dict = {
        "run": "colab-1789658250172468461",
        "notices": len(rows),
        "notice_amount_confirmed_won": NOTICE_CONFIRMED,
        "source_columns": "판정만 사용. 막힌_단계는 쓰지 않는다",
        "notices_without_amount": missing_amount,
        "gates": [],
    }

    for name, item, low, high, target in GATES:
        base_pairs: list[tuple[int, int]] = []
        gated_pairs: list[tuple[int, int]] = []
        killed_tp: list[str] = []
        killed_fp: list[str] = []
        for row in rows:
            judged = (row.get("items") or {}).get(item) or {}
            pred = 1 if judged.get("판정") == 1 else 0
            truth = 1 if (row.get("truth") or {}).get(item) == 1 else 0
            amount = amounts.get(row["id"])
            # 금액을 못 읽으면 거르지 않는다. 결손을 음성 근거로 쓰지 않는다.
            inside = amount is None or (
                (low is None or amount >= low) and (high is None or amount < high))
            gated = pred if (pred == 0 or inside) else 0
            base_pairs.append((pred, truth))
            gated_pairs.append((gated, truth))
            if pred == 1 and gated == 0:
                (killed_tp if truth == 1 else killed_fp).append(row["id"])

        before = score(base_pairs)
        after = score(gated_pairs)
        matched = None
        if target is not None:
            matched = (
                (after["tp"], after["fp"], after["fn"]) == target[:3]
                and abs(after["f1"] - target[3]) < 0.0005
            )
        report["gates"].append({
            "name": name,
            "item": item,
            "floor_won": low,
            "ceiling_won": high,
            "support": before["tp"] + before["fn"],
            "before": before,
            "after": after,
            "handoff_target": target,
            "target_matched": matched,
            "masked_true_positives": killed_tp,
            "masked_false_positives_count": len(killed_fp),
        })

    # newline="" 이 없으면 Windows 에서 LF 가 CRLF 로 바뀐다. 저장소 규약은 LF 다.
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="")

    print(f"공고 {report['notices']}건, 금액 미확인 {len(missing_amount)}건")
    print(f"{'게이트':<24}{'전 TP/FP/FN·F1':<26}{'후 TP/FP/FN·F1':<26}{'인수인계 목표':<24}일치")
    for data in report["gates"]:
        b, a, t = data["before"], data["after"], data["handoff_target"]
        bs = f"{b['tp']}/{b['fp']}/{b['fn']} · {b['f1']:.3f}"
        as_ = f"{a['tp']}/{a['fp']}/{a['fn']} · {a['f1']:.3f}"
        ts = "—" if t is None else f"{t[0]}/{t[1]}/{t[2]} · {t[3]:.3f}"
        flag = "—" if data["target_matched"] is None else ("예" if data["target_matched"] else "아니오")
        print(f"{data['name']:<24}{bs:<26}{as_:<26}{ts:<24}{flag}")
        if data["masked_true_positives"]:
            print(f"    게이트가 지운 TP: {', '.join(data['masked_true_positives'])}")
    print(f"\n기록: {OUT.relative_to(REPO).as_posix()}")


if __name__ == "__main__":
    main()
