"""Pick S7-12 per-item thresholds on dev from a GPU round that recorded `item_p1`. No model calls.

One replay per grid value applies that cut to every item at once. A cut on one item only moves
that item's cells, so each item's dev F1 at each cut is read from those replays; the best cut per
item wins, ties keep the argmax answer (no threshold). A final replay with the chosen cuts checks
that the items did not interact.

    python -X utf8 tools/tune_thresholds.py --case reports/runs/<run>/dev-debug --out <new dir>

Dev has 5-8 positives per item: the chosen cuts fit dev and may not transfer (accepted risk).
"""

import argparse
import csv
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
GRID = (0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99, 0.999)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def item_f1(rows, truth, item):
    tp = sum(int(r[item]) and truth[r["id"]][item] == "1" for r in rows)
    fp = sum(int(r[item]) and truth[r["id"]][item] == "0" for r in rows)
    fn = sum(not int(r[item]) and truth[r["id"]][item] == "1" for r in rows)
    return (2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0), (tp, fp, fn)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--case", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--input", default=str(ROOT / "open/dev.jsonl"))
    parser.add_argument("--truth", default=str(ROOT / "open/dev_labels.csv"))
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    replay_run = load("replay_run", ROOT / "tools/replay_run.py")
    script = load("submission", ROOT / "script.py")
    if not replay_run.saved_probabilities(args.case):
        raise SystemExit("this run recorded no item_p1 - it predates the logprob code")
    with open(args.truth, encoding="utf-8") as stream:
        truth = {r["id"]: r for r in csv.DictReader(stream)}

    def run(thresholds):
        script.ITEM_THRESHOLDS.clear()
        script.ITEM_THRESHOLDS.update(thresholds)
        result = replay_run.replay(script, args.case, input_path=args.input, data_dir=str(ROOT / "open/data"))
        return [{k: str(v) for k, v in row.items()} for row in result["rows"]]

    base = run({})
    best = {item: (item_f1(base, truth, item)[0], None) for item in script.ITEMS}
    table = {item: {"argmax": item_f1(base, truth, item)} for item in script.ITEMS}
    for cut in GRID:
        rows = run({item: cut for item in script.ITEMS})
        for item in script.ITEMS:
            f1, cells = item_f1(rows, truth, item)
            table[item][str(cut)] = (f1, cells)
            if f1 > best[item][0] + 1e-12:
                best[item] = (f1, cut)
    chosen = {item: cut for item, (_, cut) in best.items() if cut is not None}
    final = run(chosen)
    macro = lambda rows: sum(item_f1(rows, truth, i)[0] for i in script.ITEMS) / len(script.ITEMS)  # noqa: E731
    summary = {"case": args.case, "chosen": chosen, "dev_macro_argmax": macro(base),
               "dev_macro_chosen": macro(final),
               "per_item": {item: {"argmax": table[item]["argmax"], "chosen_cut": chosen.get(item),
                                   "chosen": item_f1(final, truth, item)} for item in script.ITEMS},
               "grid": {item: table[item] for item in script.ITEMS}}
    (out / "thresholds.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8", newline="\n")
    print(f"dev Macro argmax {summary['dev_macro_argmax']:.6f} -> chosen {summary['dev_macro_chosen']:.6f}")
    for item, cut in sorted(chosen.items(), key=lambda kv: int(kv[0][1:])):
        a, c = summary["per_item"][item]["argmax"], summary["per_item"][item]["chosen"]
        print(f"  {item:4} cut {cut:<6} F1 {a[0]:.3f} {a[1]} -> {c[0]:.3f} {c[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
