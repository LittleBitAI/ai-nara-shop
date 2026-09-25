"""B10 — turn labeler facts into v21 verdicts with the operating floor table, then apply the gate.

The labeler (`reports/team-b/b10-v21-quote-share/question-v21-facts.md`) only reads facts from the
notice. The verdict is code: the same floor as `script.v21_minimum_share()`. The rules below were
written in docs/tasks/b-v21-quote-share.md before any facts run.

    python -X utf8 experiments/b10_v21_facts_verdict.py calib --facts <dev facts.jsonl>
    python -X utf8 experiments/b10_v21_facts_verdict.py gate --facts <dev facts.jsonl> \\
        --unlabeled-facts <84 facts.jsonl>
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import script  # noqa: E402
from label_bundle import malformed  # noqa: E402

TP_CELLS = ("PPS-DEV-25", "PPS-DEV-049", "PPS-DEV-055", "PPS-DEV-058", "PPS-DEV-059")
F1 = 10 / 11                      # dev v21 5/0/1 on main c77a305
NUMBER = (int, float, type(None))
SCHEMA = {"joint_contract": str, "method": str, "min_share_percent": NUMBER,
          "quote": (str, type(None)), "정보부족": bool}


def wilson(k: int, n: int, z: float):
    p, d = k / n, 1 + z * z / n
    centre, spread = p + z * z / (2 * n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - spread) / d, (centre + spread) / d


def verdict(facts: dict, rec: dict) -> int:
    """1 when the notice sets a per-member minimum below the floor. Unobservable counts as 1,
    and so does a reply whose values are not the question's shapes."""
    if facts.get("정보부족") is True or malformed(facts, SCHEMA):
        return 1
    share = facts.get("min_share_percent")
    if facts.get("joint_contract") == "barred" or facts.get("method") == "분담이행" \
            or not isinstance(share, (int, float)) or isinstance(share, bool):
        return 0
    floor = script.v21_minimum_share(rec)
    return int(floor is not None and share < floor)


def load(path, input_path):
    facts = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            facts[row["id"]] = row["facts"]
    recs = {rec["id"]: rec for rec in script.iter_records(str(input_path), None) if rec["id"] in facts}
    return {i: verdict(facts[i], recs[i]) for i in facts}, facts


def calibration(path):
    verdicts, facts = load(path, ROOT / "open/dev.jsonl")
    with (ROOT / "open/dev_labels.csv").open(encoding="utf-8") as stream:
        truth = {row["id"]: int(row["v21"]) for row in csv.DictReader(stream)}
    hits = sum(verdicts[i] for i in TP_CELLS)
    negatives = [i for i in verdicts if truth[i] == 0]
    for i in sorted(verdicts):
        if verdicts[i] != truth[i]:
            print(f"disagree {i} truth={truth[i]} verdict={verdicts[i]} facts={facts[i]}")
    s = wilson(hits, len(TP_CELLS), 1.96)[0]
    print(f"TP cells {hits}/{len(TP_CELLS)} · s={s:.3f} · negatives judged 1: "
          f"{sum(verdicts[i] for i in negatives)}/{len(negatives)}")
    return hits, s


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("calib", "gate"))
    parser.add_argument("--facts", required=True)
    parser.add_argument("--unlabeled-facts")
    args = parser.parse_args(argv)
    hits, s = calibration(args.facts)
    if hits <= 3:
        print("rule 1: TP cells 3/5 or fewer — reject")
        return 0
    if args.command == "gate":
        verdicts, _ = load(args.unlabeled_facts, ROOT / "open/train_unlabeled.jsonl")
        k, n = sum(verdicts.values()), len(verdicts)
        upper = wilson(k, n, 2.498)[1]
        print(f"deletion set k={k}/{n} · 98.75% Wilson upper {upper:.4f} · threshold s·F/2 {s * F1 / 2:.4f}")
        print("adopt" if upper < s * F1 / 2 else "reject")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
