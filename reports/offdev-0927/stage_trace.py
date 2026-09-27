"""Which stage decided each wrong cell off dev. No model calls.

Replays saved responses with the current `script.py` and records three values per cell:
the model's answer (after thresholds, when the run kept probabilities), the value after the
SME and company-size calls, and the final value after `postprocess`. A wrong cell is charged to
the last stage that set it: `model`, `calls` (SME / company-size) or `postprocess`.

  python -X utf8 reports/offdev-0927/stage_trace.py --labels <merged csv> \
      --case <run>/uNN/output --input <that chunk's records> [--case ... --input ...]
"""

import argparse
import collections
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import replay_run  # noqa: E402


def charge(label, model, calls, final):
    """The stage that last set a wrong final value, or None when the cell is right."""
    if final == label:
        return None
    if calls != final:
        return "postprocess"
    if model != calls:
        return "calls"
    return "model"


def trace(script, case, input_path, data_dir):
    texts = replay_run.saved_responses(case)
    probabilities = replay_run.saved_probabilities(case)
    seen = {}

    def spy(parsed, rec):
        seen[rec["id"]] = {v: parsed[v]["위반여부"] for v in script.ITEMS}
        return script.postprocess(parsed, rec)

    result = replay_run.replay(script, case, input_path=input_path, data_dir=data_dir, postprocess=spy)
    out = {}
    for row in result["rows"]:
        parsed, _ = script.parse_judgment(texts["baseline"][row["id"]])
        if getattr(script, "apply_thresholds", None):
            parsed = script.apply_thresholds(parsed, probabilities.get(row["id"]))
        out[row["id"]] = {v: (parsed[v]["위반여부"], seen[row["id"]][v], row[v]) for v in script.ITEMS}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", required=True)
    parser.add_argument("--case", action="append", required=True)
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--data-dir", default=str(ROOT / "open/data"))
    args = parser.parse_args(argv)
    if len(args.case) != len(args.input):
        parser.error("--case and --input come in pairs")
    script = replay_run.load_module(ROOT / "script.py", "submission")
    cells = {}
    for case, input_path in zip(args.case, args.input):
        cells.update(trace(script, case, input_path, args.data_dir))
    with open(args.labels, encoding="utf-8") as stream:
        labels = {r["id"]: r for r in csv.DictReader(stream)}
    table = collections.defaultdict(collections.Counter)
    for identifier, truth in labels.items():
        if identifier not in cells:
            continue
        for item in script.ITEMS:
            if truth[item] == "":
                continue
            label = int(truth[item])
            stage = charge(label, *cells[identifier][item])
            if stage:
                table[item][("FN" if label else "FP") + ":" + stage] += 1
    print(json.dumps({"scored": sum(i in cells for i in labels), **{k: dict(v) for k, v in sorted(
        table.items(), key=lambda kv: int(kv[0][1:]))}}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    assert charge(1, 1, 1, 1) is None
    assert charge(1, 0, 0, 0) == "model"
    assert charge(1, 1, 0, 0) == "calls"
    assert charge(1, 1, 1, 0) == "postprocess"
    assert charge(0, 0, 0, 1) == "postprocess"
    sys.exit(main())
