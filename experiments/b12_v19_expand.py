"""B12 — grow the v19 answer set beyond dev 200 with the v2 facts labeler.

Frame: a notice can be a v19 positive only if its text names a supply or technical-support pledge
(FILTER). On dev the filter keeps 22 of 200 notices and all 6 v19 positives. Unlabeled: 1,231 of
20,000. We label a seeded random sample inside the filter; notices outside it are v19=0 by the frame.
Every sampled notice carries weight = filtered / sampled so totals estimate the 1,231.

    python -X utf8 experiments/b12_v19_expand.py ids --n 300           # sample IDs, in order
    python -X utf8 experiments/b12_v19_expand.py dev-ids               # dev notices inside the filter
    python -X utf8 experiments/b12_v19_expand.py score --facts <dev facts>      # calibration
    python -X utf8 experiments/b12_v19_expand.py dataset --facts <unlabeled facts> --out <csv>
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import script  # noqa: E402
import b11_b_facts_v2_verdict as v2  # noqa: E402

FILTER = re.compile(r"(?:물품\s*공급|제품\s*공급|공급|기술\s*지원|A\s*/?\s*S)[^\n.]{0,15}확약")
SEED = 20260924
UNLABELED = ROOT / "open/train_unlabeled.jsonl"
DEV = ROOT / "open/dev.jsonl"


def filtered(path):
    return [r["id"] for r in script.iter_records(str(path), None) if FILTER.search(script._body(r))]


SCHEMA = {"v19_documents": [v2.V19_DOCUMENT], "정보부족": bool}


def load(path):
    """Facts by id. A reply whose values are not the question's shapes is dropped and named."""
    facts = {json.loads(l)["id"]: json.loads(l)["facts"]
             for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()}
    failed = sorted(i for i, f in facts.items() if v2.v1.shape_errors(f, SCHEMA))
    if failed:
        print(f"형식 실패 {len(failed)} {failed}", file=sys.stderr)
    return {i: f for i, f in facts.items() if i not in failed}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("ids", "dev-ids", "score", "dataset"))
    parser.add_argument("--n", type=int, default=300)
    parser.add_argument("--facts")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    if args.command == "ids":
        pool = sorted(filtered(UNLABELED))
        print(",".join(random.Random(SEED).sample(pool, args.n)))
        print(f"pool {len(pool)}", file=sys.stderr)
    elif args.command == "dev-ids":
        print(",".join(filtered(DEV)))
    elif args.command == "score":
        facts = load(args.facts)
        recs = {r["id"]: r for r in script.iter_records(str(DEV), None) if r["id"] in facts}
        with (ROOT / "open/dev_labels.csv").open(encoding="utf-8") as stream:
            truth = {r["id"]: int(r["v19"]) for r in csv.DictReader(stream)}
        pred = {i: v2.v19(facts[i], recs[i]) for i in facts}
        outside = sum(truth.values()) - sum(truth[i] for i in facts)   # positives the filter would miss
        tp = sum(pred[i] and truth[i] for i in facts)
        fp = sum(pred[i] and not truth[i] for i in facts)
        fn = sum(truth[i] and not pred[i] for i in facts) + outside
        f1 = 2 * tp / (2 * tp + fp + fn)
        for i in sorted(facts):
            if pred[i] != truth[i]:
                print(f"disagree {i} truth={truth[i]} pred={pred[i]} {facts[i].get('v19_documents')}")
        print(f"dev 200 (filter + labeler): TP {tp} FP {fp} FN {fn} · F1 {f1:.3f} · "
              f"{'pass' if f1 >= 0.80 else 'fail'} (>= 0.80)")
    else:
        facts = load(args.facts)
        wanted = set(facts)
        recs = {r["id"]: r for r in script.iter_records(str(UNLABELED), None) if r["id"] in wanted}
        pool = len(filtered(UNLABELED))
        weight = pool / len(facts)
        with open(args.out, "w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["id", "v19", "weight", "정보부족", "evidence"])
            for i in sorted(facts):
                docs = [d for d in facts[i].get("v19_documents") or [] if isinstance(d, dict)]
                label = v2.v19(facts[i], recs[i])
                # the timing of the document that made it positive, not the first one listed
                evidence = next((d["timing"] for d in docs
                                 if v2.v19({"v19_documents": [d]}, recs[i])), "")
                writer.writerow([i, label, f"{weight:.4f}", bool(facts[i].get("정보부족")), evidence])
        positives = sum(v2.v19(facts[i], recs[i]) for i in facts)
        print(f"labelled {len(facts)} · v19=1 {positives} · weight {weight:.3f} · "
              f"estimated positives in the 20,000: {positives * weight:.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
