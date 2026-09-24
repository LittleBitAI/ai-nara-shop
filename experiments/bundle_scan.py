"""Score every replayed candidate against a base CSV on dev: Macro delta and the items that moved.

    python -X utf8 experiments/bundle_scan.py --dir <folder with base/ and one folder per candidate>
"""

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS = [f"v{i}" for i in range(1, 25)]


def f1s(path, truth):
    rows = {r["id"]: r for r in csv.DictReader(open(path, encoding="utf-8"))}
    out = {}
    for item in ITEMS:
        tp = sum(rows[i][item] == "1" and truth[i][item] == "1" for i in truth)
        fp = sum(rows[i][item] == "1" and truth[i][item] == "0" for i in truth)
        fn = sum(rows[i][item] == "0" and truth[i][item] == "1" for i in truth)
        out[item] = (2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0, (tp, fp, fn))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    args = parser.parse_args(argv)
    folder = Path(args.dir)
    truth = {r["id"]: r for r in csv.DictReader(open(ROOT / "open/dev_labels.csv", encoding="utf-8"))}
    base = f1s(folder / "base/submission.csv", truth)
    base_macro = sum(v[0] for v in base.values()) / 24
    print(f"base {base_macro:.6f}")
    results = []
    for sub in sorted(p for p in folder.iterdir() if p.is_dir() and p.name != "base"):
        csv_path = sub / "submission.csv"
        if not csv_path.is_file():
            results.append((None, sub.name, "no output"))
            continue
        got = f1s(csv_path, truth)
        delta = sum(v[0] for v in got.values()) / 24 - base_macro
        moved = [f"{i} {base[i][1]}->{got[i][1]}" for i in ITEMS if got[i][1] != base[i][1]]
        results.append((delta, sub.name, "; ".join(moved)))
    for delta, name, moved in sorted(results, key=lambda r: -(r[0] if r[0] is not None else -9)):
        print(f"{'  n/a  ' if delta is None else f'{delta:+.5f}'}  {name:34} {moved}")


if __name__ == "__main__":
    main()
