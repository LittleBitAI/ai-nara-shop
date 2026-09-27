"""Score replayed CSVs against the off-dev label sets, whole and per split half. No model calls.

Blank label cells (v9, v24, excluded items) are not labels and are skipped. Macro is over the items
that have labels; an item whose TP+FP+FN is 0 scores 0, the team rule for local subsets (docs/data.md).
Halves follow `half(id)` in reports/labels-3000/pick.py.

  python -X utf8 reports/offdev-0927/score_offdev.py --pred <submission.csv> [...] --labels <merged csv> [...]
"""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reports" / "labels-3000"))
from pick import half  # noqa: E402

ITEMS = [f"v{i}" for i in range(1, 25)]


def score(pred, labels, keep=lambda identifier: True):
    counts = {}
    for identifier, truth in labels.items():
        if identifier not in pred or not keep(identifier):
            continue
        for item in ITEMS:
            if truth[item] == "":
                continue
            c = counts.setdefault(item, [0, 0, 0])
            t, p = int(truth[item]), int(pred[identifier][item])
            c[0] += t & p
            c[1] += p & (1 - t)
            c[2] += t & (1 - p)
    f1 = {k: (2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0) for k, (tp, fp, fn) in counts.items()}
    return {"macro": round(sum(f1.values()) / len(f1), 6) if f1 else None,
            "items": {k: counts[k] for k in ITEMS if k in counts}}


def load(paths):
    rows = {}
    for path in paths:
        with open(path, encoding="utf-8") as stream:
            rows.update({r["id"]: r for r in csv.DictReader(stream)})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred", nargs="+", required=True)
    parser.add_argument("--labels", nargs="+", required=True)
    args = parser.parse_args(argv)
    pred, labels = load(args.pred), load(args.labels)
    scored = sum(i in pred for i in labels)
    print(json.dumps({"scored": scored, "all": score(pred, labels),
                      "A": score(pred, labels, lambda i: half(i) == "A")["macro"],
                      "B": score(pred, labels, lambda i: half(i) == "B")["macro"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    demo = score({"x": {**{v: "0" for v in ITEMS}, "v1": "1"}}, {"x": {**{v: "0" for v in ITEMS}, "v1": "1", "v9": ""}})
    assert demo["items"]["v1"] == [1, 0, 0] and "v9" not in demo["items"]
    sys.exit(main())
