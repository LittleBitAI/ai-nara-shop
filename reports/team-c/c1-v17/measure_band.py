"""C1 — v17 의 금액 구간 게이트를 보관 회차 **전부**에 씌워 잰다.

v17 = 1억원 미만 일반물품 중소기업 제한. 부재탐지가 아니며 제한이 **있는 것**이 위반이다.
따라서 구간은 `추정가격 < 1억` 이고, 그 밖에서 켜진 양성은 적용 대상이 아니다.

**한 회차로 재지 않는다.** 같은 `script.py` 가 회차마다 v17 을 TP 2~4 · FP 39~43 로 낸다.
한 회차의 FP 감소는 게이트 효과인지 churn 인지 갈리지 않는다. 그래서 보관된 모든
`dev*/submission.csv` 에 같은 게이트를 씌우고 **회차 이름과 함께** 낸다.

모델을 부르지 않는다. 제출 CSV 를 새로 만들지 않는다.

실행:
    py -X utf8 reports/team-c/c1-v17/measure_band.py
"""

from __future__ import annotations

import csv
import glob
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEV = REPO / "open/dev.jsonl"
LABELS = REPO / "open/dev_labels.csv"
OUT = Path(__file__).resolve().parent / "band-result.json"

# 금액 읽기는 후보에서 가져온다. 복제본을 두지 않는다.
sys.path.insert(0, str(REPO))
from experiments.sme_candidate import SME_BAND_FLOOR_WON, estimated_price  # noqa: E402

ITEM = "v17"
# 국가 시행령 제21조①10호 **가목**, 지방 제20조①12호 가목, 판로지원법 시행령 제2조의2①1호.
# 1억원 미만 구간의 방법은 소기업·소상공인이며 중소기업으로 넓히는 것이 v17 위반이다.
# 1억 이상은 이 항목의 적용 대상이 아니다 — 그 구간은 v15·v14 가 본다.
BAND_CEILING_WON = SME_BAND_FLOOR_WON


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def score(pairs: list[tuple[int, int]]) -> dict:
    tp = sum(1 for p, t in pairs if p and t)
    fp = sum(1 for p, t in pairs if p and not t)
    fn = sum(1 for p, t in pairs if not p and t)
    denom = 2 * tp + fp + fn
    return {"tp": tp, "fp": fp, "fn": fn, "f1": (2 * tp / denom) if denom else 0.0}


def main() -> int:
    amounts = {r["id"]: estimated_price(r) for r in load_jsonl(DEV)}
    with LABELS.open(encoding="utf-8", newline="") as stream:
        truth = {r["id"]: int(r[ITEM]) for r in csv.DictReader(stream)}

    paths = sorted(Path(p) for p in glob.glob(str(REPO / "reports/runs/*/dev*/submission.csv")))
    if not paths:
        print("error: 보관된 submission.csv 가 없다", file=sys.stderr)
        return 1

    report: dict = {
        "item": ITEM,
        "band": f"추정가격 < {BAND_CEILING_WON:,}",
        "purpose": "구간 게이트의 FP 감소와 TP 보존을 회차마다 잰다",
        "caveat": "절대 수치는 회차에 딸려 있다. 회차 이름 없이 인용하지 않는다",
        "runs": [],
    }

    print(f"{ITEM} · 구간 {report['band']} · 보관 회차 {len(paths)}개")
    print(f"\n{'회차':<34}{'전 TP/FP/FN·F1':<26}{'후 TP/FP/FN·F1':<26}{'지운 TP'}")

    killed_all: set[str] = set()
    for path in paths:
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        before, after, killed = [], [], []
        for row in rows:
            pred = 1 if row[ITEM] == "1" else 0
            label = 1 if truth.get(row["id"]) == 1 else 0
            amount = amounts.get(row["id"])
            # 금액을 못 읽으면 거르지 않는다. 결손은 음성 근거가 아니다.
            inside = amount is None or amount < BAND_CEILING_WON
            gated = pred if (pred == 0 or inside) else 0
            before.append((pred, label))
            after.append((gated, label))
            if pred and not gated and label:
                killed.append(row["id"])
        killed_all.update(killed)

        b, a = score(before), score(after)
        run_id = path.parent.parent.name + "/" + path.parent.name
        report["runs"].append({"run": run_id, "before": b, "after": a, "killed_tp": killed})
        bs = f"{b['tp']}/{b['fp']}/{b['fn']} · {b['f1']:.4f}"
        as_ = f"{a['tp']}/{a['fp']}/{a['fn']} · {a['f1']:.4f}"
        print(f"{run_id:<34}{bs:<26}{as_:<26}{', '.join(killed) or '0'}")

    fps = [r["before"]["fp"] - r["after"]["fp"] for r in report["runs"]]
    tps = [r["before"]["tp"] - r["after"]["tp"] for r in report["runs"]]
    report["fp_removed"] = {"min": min(fps), "max": max(fps)}
    report["tp_removed"] = {"min": min(tps), "max": max(tps)}
    report["killed_tp_any_run"] = sorted(killed_all)

    print(f"\nFP 감소 {min(fps)}~{max(fps)}건 · TP 감소 {min(tps)}~{max(tps)}건 "
          f"({len(paths)}개 회차 전부)")
    if killed_all:
        print(f"!! 구간이 지운 TP 가 있다: {sorted(killed_all)} — 조문을 다시 읽어야 한다")
    else:
        print("구간이 지운 TP 는 어느 회차에도 없다.")

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="")
    print(f"\n기록: {OUT.relative_to(REPO).as_posix()}")
    print("절대 수치는 회차에 딸려 있다. 회차 이름 없이 인용하지 않는다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
