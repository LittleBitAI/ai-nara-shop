"""Per-item labeler calibration on dev: TP/FP/FN, F1 and the verdict fixed before the run.

F1 >= 0.80 trust, 0.60 <= F1 < 0.80 conditional, below 0.60 exclude (docs/tasks/plan-0926-0929.md).
An item with no dev positive in the set cannot be calibrated and is reported as such.

  python -X utf8 reports/labels-600/calibrate.py reports/labels-600/calib120/luna-shard*.jsonl
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ITEMS = [f"v{i}" for i in range(1, 25)]
TRUST, CONDITIONAL = 0.80, 0.60


def verdict(f1, positives):
    if positives == 0:
        return "no positives"
    return "trust" if f1 >= TRUST else "conditional" if f1 >= CONDITIONAL else "exclude"


def main(paths):
    truth = {r["id"]: r for r in csv.DictReader((ROOT / "open/dev_labels.csv").open(encoding="utf-8"))}
    labels = {}
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                labels[record["id"]] = record["labels"]
    rows = []
    for item in ITEMS:
        tp = sum(truth[i][item] == "1" and labels[i][item]["위반여부"] == 1 for i in labels)
        fp = sum(truth[i][item] == "0" and labels[i][item]["위반여부"] == 1 for i in labels)
        fn = sum(truth[i][item] == "1" and labels[i][item]["위반여부"] == 0 for i in labels)
        f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0
        rows.append({"item": item, "positives": tp + fn, "tp": tp, "fp": fp, "fn": fn,
                     "f1": round(f1, 3), "verdict": verdict(f1, tp + fn)})
    print(f"notices {len(labels)}")
    for row in rows:
        print(f"{row['item']:>4} pos {row['positives']} {row['tp']}/{row['fp']}/{row['fn']} "
              f"F1 {row['f1']:.3f} {row['verdict']}")
    counts = {v: sum(r["verdict"] == v for r in rows) for v in ("trust", "conditional", "exclude", "no positives")}
    print(counts)
    out = Path(__file__).with_name("calibration.json")
    out.write_text(json.dumps({"notices": len(labels), "rule": {"trust": TRUST, "conditional": CONDITIONAL},
                               "items": rows}, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
