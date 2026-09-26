"""Merge the two labelers into one label set per sample, taking each item from the labeler that calibrated better.

The choice per item was made after seeing both dev-120 calibrations (docs/tasks/labels-600.md), so the combined
verdicts are optimistic; v10 and v20 were revised on all of dev 200 and are marked dev-fitted. Excluded items are
written as empty cells: they are not labels.

  python -X utf8 reports/labels-600/merge_labels.py
"""

import csv
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
sys.path.insert(0, str(ROOT / "experiments"))
import a_facts_verdict as facts_verdict  # noqa: E402
import a_focus_verdict as focus_verdict  # noqa: E402

ITEMS = [f"v{i}" for i in range(1, 25)]
FACTS_ITEMS = {"v19": "trust", "v11": "conditional", "v18": "conditional", "v16": "conditional", "v4": "conditional",
               "v10": "conditional (dev-fitted)"}
# v20 from the focused question; its dev 200 score was reached by revising on those 200.
FOCUS_ITEMS = {"v20": "conditional (dev-fitted)"}
EXCLUDED = {"v1", "v9", "v24"}


def main():
    wide = {r["item"]: r["verdict"] for r in json.loads((HERE / "calibration.json").read_text(encoding="utf-8"))["items"]}
    source = {}
    for item in ITEMS:
        if item in EXCLUDED:
            source[item] = {"labeler": None, "verdict": "exclude"}
        elif item in FACTS_ITEMS:
            source[item] = {"labeler": "facts", "verdict": FACTS_ITEMS[item]}
        elif item in FOCUS_ITEMS:
            source[item] = {"labeler": "focus", "verdict": FOCUS_ITEMS[item]}
        else:
            source[item] = {"labeler": "24-item", "verdict": wide[item]}
    wanted = set()
    for sample in ("sealed", "diag"):
        wanted |= set((HERE / f"{sample}-ids.txt").read_text(encoding="utf-8").split())
    records = {r["id"]: r for r in facts_verdict.script.iter_records(str(ROOT / "open/train_unlabeled.jsonl"))
               if r["id"] in wanted}
    for sample in ("sealed", "diag"):
        wide_labels, fact_rows, focus_rows = {}, {}, {}
        for path in sorted(glob.glob(str(HERE / "facts" / "focus3-600" / "luna-*.jsonl"))):
            for line in Path(path).read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                focus_rows[row["id"]] = row["facts"]
        for path in sorted(glob.glob(str(HERE / sample / "luna-*.jsonl"))):
            for line in Path(path).read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                wide_labels[row["id"]] = row["labels"]
        for path in sorted(glob.glob(str(HERE / "facts" / sample / "luna-*.jsonl"))):
            for line in Path(path).read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                fact_rows[row["id"]] = row["facts"]
        out = HERE / "merged" / f"{sample}.csv"
        out.parent.mkdir(exist_ok=True)
        with out.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["id", *ITEMS])
            for identifier in sorted(wide_labels):
                row = [identifier]
                for item in ITEMS:
                    labeler = source[item]["labeler"]
                    if labeler is None:
                        row.append("")
                    elif labeler == "facts":
                        f = fact_rows[identifier]
                        row.append(0 if f.get("정보부족") is True
                                   else facts_verdict.VERDICTS[item](f, records[identifier]))
                    elif labeler == "focus":
                        row.append(focus_verdict.label(item, focus_rows[identifier], records[identifier]))
                    else:
                        row.append(wide_labels[identifier][item]["위반여부"])
                writer.writerow(row)
        print(f"{out.relative_to(ROOT).as_posix()} rows={len(wide_labels)}")
    (HERE / "merged" / "sources.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
