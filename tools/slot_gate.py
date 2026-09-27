"""Adoption gate for post-processing candidates: replay base and candidate on the same saved responses, then
apply the 9/27 rules plus a paired bootstrap. No model call; the verdict is PASS or FAIL, never a hold.

Rules (plan-0926-0929 "Adoption rule from 9/27", and a 95% bar on top):
  1. Macro over the labelled items rises on every off-dev pool.
  2. It rises on both split halves (`half(id)`) of every off-dev pool.
  3. No trusted item (labels-600 sources.json) loses more than one net (TP - FP) cell on any off-dev pool.
  4. Dev replay drops by no more than 0.01 Macro.
  5. On every off-dev pool the candidate beats the base in at least 95% of notice resamples.
Notices in --exclude (the labeler's 수의계약 positives, reports/labels-3000/private-ids.txt) are not scored.

  python -X utf8 tools/slot_gate.py --base <script.py> --candidate <script.py> \
      --pool dev <case> <input.jsonl> open/dev_labels.csv \
      --pool offdev600 <case> <input.jsonl> <diag.csv>,<sealed.csv> \
      --pool labels2000 <case>,<case>,... <input>,<input>,... reports/labels-3000/merged.csv \
      --exclude reports/labels-3000/private-ids.txt --out <new dir>
A pool with several cases lists cases and inputs in the same order, comma-separated.
"""

import argparse
import csv
import io
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "reports" / "labels-3000"))
import replay_run  # noqa: E402
from pick import half  # noqa: E402

ITEMS = [f"v{i}" for i in range(1, 25)]
RESAMPLES = 2000
SEED = 20260928


def f1(c):
    tp, fp, fn = c
    return 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0


def cells(pred, truth, ids):
    """Per notice, per labelled item: (tp, fp, fn)."""
    return [{v: (t[v] & p[v], p[v] & (1 - t[v]), t[v] & (1 - p[v]))
             for v in ITEMS if t[v] is not None}
            for t, p in ((truth[i], pred[i]) for i in ids)]


def total(rows):
    out = {}
    for row in rows:
        for v, c in row.items():
            x = out.setdefault(v, [0, 0, 0])
            for k in range(3):
                x[k] += c[k]
    return out


def macro(counts):
    return sum(f1(c) for c in counts.values()) / len(counts) if counts else 0.0


def bootstrap(base_rows, cand_rows, n=RESAMPLES, seed=SEED):
    """Share of notice resamples where the candidate's Macro beats the base's."""
    rng = random.Random(seed)
    wins = 0
    for _ in range(n):
        pick = [rng.randrange(len(base_rows)) for _ in base_rows]
        wins += macro(total(cand_rows[k] for k in pick)) > macro(total(base_rows[k] for k in pick))
    return wins / n


def read_labels(paths):
    out = {}
    for path in paths:
        with open(path, encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                out[row["id"]] = {v: None if row[v] == "" else int(row[v]) for v in ITEMS}
    return out


def predictions(script, cases, inputs):
    out = {}
    for case, input_path in zip(cases, inputs):
        result = replay_run.replay(script, case, input_path=input_path, data_dir=ROOT / "open" / "data")
        for row in csv.DictReader(io.StringIO(replay_run.to_csv_bytes(script, result["rows"]).decode("utf-8"))):
            out[row["id"]] = {v: int(row[v]) for v in ITEMS}
    return out


def judge(pools, trusted):
    """pools: {name: (base_pred, cand_pred, truth, ids)}. Returns (verdict, report)."""
    report, failed = {}, []
    for name, (base, cand, truth, ids) in pools.items():
        b, c = cells(base, truth, ids), cells(cand, truth, ids)
        tb, tc = total(b), total(c)
        entry = {"notices": len(ids), "base": round(macro(tb), 6), "candidate": round(macro(tc), 6),
                 "moved": {v: [tb[v], tc[v]] for v in tb if tb[v] != tc[v]}}
        if name == "dev":
            if macro(tc) < macro(tb) - 0.01:
                failed.append("4: dev drops by more than 0.01")
        else:
            if macro(tc) <= macro(tb):
                failed.append(f"1: {name} Macro does not rise")
            for h in "AB":
                keep = [k for k, i in enumerate(ids) if half(i) == h]
                gain = macro(total(c[k] for k in keep)) - macro(total(b[k] for k in keep))
                entry[f"half_{h}"] = round(gain, 6)
                if gain <= 0:
                    failed.append(f"2: {name} half {h} does not rise")
            for v in trusted:
                if v in tb and (tb[v][0] - tb[v][1]) - (tc[v][0] - tc[v][1]) > 1:
                    failed.append(f"3: {name} trusted {v} loses more than one net cell")
            entry["p_gain"] = bootstrap(b, c)
            if entry["p_gain"] < 0.95:
                failed.append(f"5: {name} gains in only {entry['p_gain']:.3f} of resamples")
        report[name] = entry
    return ("PASS" if not failed else "FAIL"), {"failed": failed, "pools": report}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--pool", nargs=4, action="append", required=True,
                        metavar=("NAME", "CASES", "INPUTS", "LABELS"))
    parser.add_argument("--exclude")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"{out} already exists")
    base = replay_run.load_module(Path(args.base), "gate_base")
    cand = replay_run.load_module(Path(args.candidate), "gate_candidate")
    drop = set(Path(args.exclude).read_text(encoding="utf-8").split()) if args.exclude else set()
    sources = json.loads((ROOT / "reports/labels-600/merged/sources.json").read_text(encoding="utf-8"))
    trusted = [v for v, s in sources.items() if s["verdict"].startswith("trust")]
    pools = {}
    for name, cases, inputs, labels in args.pool:
        cases, inputs = cases.split(","), inputs.split(",")
        truth = read_labels(labels.split(","))
        bp, cp = predictions(base, cases, inputs), predictions(cand, cases, inputs)
        ids = [i for i in truth if i in bp and (name == "dev" or i not in drop)]
        missing = set(truth) - set(bp)
        if missing:
            raise SystemExit(f"{name}: {len(missing)} labelled notices have no replayed prediction")
        pools[name] = (bp, cp, truth, ids)
    verdict, report = judge(pools, trusted)
    out.mkdir(parents=True)
    report = {"verdict": verdict, "base": Path(args.base).name, "candidate": Path(args.candidate).name, **report}
    (out / "gate.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                   encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
