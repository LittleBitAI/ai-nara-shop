"""S7-12 thresholds on the pooled labels (dev + off-dev), with the split-half check fixed in advance. No model calls.

Only runs that saved `item_p1` can move a threshold, so every --case must have it. Label files may leave
cells blank (excluded items); blank cells are skipped. Procedure, fixed before any result:

1. For each item, replay every case once per grid cut (one cut on all items at a time; a cut only moves
   its own item's cells) and count TP/FP/FN per half(id).
2. Pick the cut that maximises the item's F1 on half A and score it on half B; then B -> A.
   Ties keep the current cut, then the higher cut.
3. An item's cut changes only when both directions beat the current cut on the held-out half.
   Its final cut is then picked on the whole pool with the same tie rule.
4. v9 and v24 keep their cuts (no off-dev labels).

  python -X utf8 reports/offdev-0927/tune_offdev.py --out <new dir> \
      --case <dir> --input <records> [--case ... --input ...] --labels <csv> [...]
"""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "reports" / "labels-3000"))
import replay_run  # noqa: E402
from pick import half  # noqa: E402

GRID = (None, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.97, 0.98, 0.99, 0.995,
        0.999, 0.9998)
FROZEN = {"v9", "v24"}


def f1(c):
    tp, fp, fn = c
    return 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0


def pick(counts, current, halves):
    """Best cut on `halves` (a set of half names); ties keep `current`, then the higher cut."""
    def total(cut):
        return [sum(counts[cut][h][k] for h in halves) for k in range(3)]
    order = sorted(counts, key=lambda c: (f1(total(c)), c == current, -1 if c is None else c), reverse=True)
    return order[0]


def decide(counts, now):
    """Steps 2-3 for one item: (pick_A, pick_B, held-out gains, passed, final cut)."""
    a, b = pick(counts, now, {"A"}), pick(counts, now, {"B"})
    gains = (f1(counts[a]["B"]) - f1(counts[now]["B"]), f1(counts[b]["A"]) - f1(counts[now]["A"]))
    # The final cut is itself held to both halves: only cuts beating the current one on A and on B.
    both = {c: v for c, v in counts.items()
            if f1(v["A"]) > f1(counts[now]["A"]) and f1(v["B"]) > f1(counts[now]["B"])}
    passed = gains[0] > 0 and gains[1] > 0 and bool(both)
    final = pick({**both, now: counts[now]}, now, {"A", "B"}) if passed else now
    return a, b, gains, passed and final != now, final


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--case", action="append", required=True)
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--labels", nargs="+", required=True)
    parser.add_argument("--data-dir", default=str(ROOT / "open/data"))
    args = parser.parse_args(argv)
    if len(args.case) != len(args.input):
        parser.error("--case and --input come in pairs")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    script = replay_run.load_module(ROOT / "script.py", "submission")
    current = dict(script.ITEM_THRESHOLDS)
    for case in args.case:
        # Every notice needs P(1) for every item, or replay silently falls back to argmax for it.
        responses = set(replay_run.saved_responses(case)["baseline"])
        probabilities = replay_run.saved_probabilities(case)
        short = [i for i in responses if not set(script.ITEMS) <= set(probabilities.get(i) or {})]
        if short:
            raise SystemExit(f"{case}: {len(short)} of {len(responses)} notices lack item_p1 for some item, "
                             f"e.g. {sorted(short)[:3]}")
    labels = {}
    for path in args.labels:
        with open(path, encoding="utf-8") as stream:
            labels.update({r["id"]: r for r in csv.DictReader(stream)})
    items = [i for i in script.ITEMS if i not in FROZEN]
    grid = sorted(set(GRID) | {current.get(i) for i in items}, key=lambda c: -1 if c is None else c)
    counts = {i: {c: {"A": [0, 0, 0], "B": [0, 0, 0]} for c in grid} for i in items}
    for cut in grid:
        script.ITEM_THRESHOLDS.clear()
        script.ITEM_THRESHOLDS.update({i: cut for i in items if cut is not None})
        script.ITEM_THRESHOLDS.update({i: current[i] for i in FROZEN if i in current})
        for case, input_path in zip(args.case, args.input):
            for row in replay_run.replay(script, case, input_path=input_path, data_dir=args.data_dir)["rows"]:
                truth = labels.get(row["id"])
                if truth is None:
                    continue
                c_half = half(row["id"])
                for i in items:
                    if truth[i] == "":
                        continue
                    t, p = int(truth[i]), int(row[i])
                    cell = counts[i][cut][c_half]
                    cell[0] += t & p
                    cell[1] += p & (1 - t)
                    cell[2] += t & (1 - p)
    script.ITEM_THRESHOLDS.clear()
    script.ITEM_THRESHOLDS.update(current)
    report, chosen = {}, dict(current)
    for i in items:
        now = current.get(i)
        a, b, gains, passed, final = decide(counts[i], now)
        if final is None:
            chosen.pop(i, None)
        else:
            chosen[i] = final
        report[i] = {"current": now, "pick_A": a, "pick_B": b, "gain_on_B": round(gains[0], 4),
                     "gain_on_A": round(gains[1], 4), "passed": passed, "final": final,
                     "pool_current": [sum(counts[i][now][h][k] for h in "AB") for k in range(3)],
                     "pool_final": [sum(counts[i][final][h][k] for h in "AB") for k in range(3)]}
    summary = {"cases": args.case, "labels": args.labels, "current": current, "chosen": chosen, "items": report}
    (out / "thresholds.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8", newline="\n")
    for i in items:
        r = report[i]
        if r["passed"]:
            print(f"{i:4} {r['current']} -> {r['final']}  pool {r['pool_current']} -> {r['pool_final']}  "
                  f"held-out gains {r['gain_on_B']:+.3f} / {r['gain_on_A']:+.3f}")
    print(f"changed: {sorted(i for i in items if report[i]['passed'] and report[i]['final'] != report[i]['current'])}")
    return 0


if __name__ == "__main__":
    toy = {None: {"A": [1, 1, 1], "B": [1, 1, 1]}, 0.5: {"A": [2, 0, 0], "B": [1, 1, 1]}}
    assert pick(toy, None, {"A"}) == 0.5 and pick(toy, 0.5, {"B"}) == 0.5 and pick(toy, None, {"B"}) is None
    # Review PR #161 round 1: a passed item's final cut must itself beat the current cut on both halves.
    import random
    rng = random.Random(0)
    for _ in range(2000):
        grid_ = [None, 0.1, 0.5, 0.7, 0.9]
        toy = {c: {h: [rng.randint(0, 5) for _ in range(3)] for h in "AB"} for c in grid_}
        now_ = rng.choice(grid_)
        _, _, _, ok, cut = decide(toy, now_)
        assert not ok or all(f1(toy[cut][h]) > f1(toy[now_][h]) for h in "AB")
    sys.exit(main())
