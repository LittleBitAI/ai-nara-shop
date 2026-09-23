"""The operating `script.py` decides exactly what the adopted candidates decide.

The candidates in `experiments/` hold the design notes, the measurements and the
per-condition tests. This file only pins the port: on every dev notice the operating
function must return what the candidate returns, and `postprocess` must apply it.
"""

import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


script = sys.modules.get("submission") or _load("submission", ROOT / "script.py")
v24 = _load("b_v24_budget_axis_candidate", ROOT / "experiments" / "b_v24_budget_axis_candidate.py")
v20 = _load("v20_sw_clause_candidate", ROOT / "experiments" / "v20_sw_clause_candidate.py")

with (ROOT / "open/dev.jsonl").open(encoding="utf-8") as stream:
    DEV = [json.loads(line) for line in stream]


def _empty():
    return {v: {"위반여부": 0, "근거문구": None} for v in script.ITEMS}


class PortedV24(unittest.TestCase):
    def test_budget_mismatch_matches_the_candidate_on_every_dev_notice(self):
        differ = [rec["id"] for rec in DEV if script.budget_mismatch(rec) != v24.budget_mismatch(rec)]
        self.assertEqual(differ, [])

    def test_postprocess_raises_v24_where_the_candidate_does(self):
        fired = [rec for rec in DEV if v24.budget_mismatch(rec)]
        self.assertTrue(fired)
        for rec in fired:
            self.assertEqual(script.postprocess(_empty(), rec)["v24"],
                             v24.postprocess(_empty(), rec)["v24"], rec["id"])


class PortedV20(unittest.TestCase):
    def test_v20_decision_matches_the_candidate_on_every_dev_notice(self):
        differ = [rec["id"] for rec in DEV if script.v20_decision(rec) != v20.v20_decision(rec)]
        self.assertEqual(differ, [])

    def test_postprocess_applies_the_decision_over_the_model(self):
        settled = [rec for rec in DEV if v20.v20_decision(rec) is not None]
        self.assertTrue(any(v20.v20_decision(rec) == 1 for rec in settled))
        for rec in settled:
            model = _empty()
            model["v20"] = {"위반여부": 1 - v20.v20_decision(rec), "근거문구": None}
            self.assertEqual(script.postprocess(model, rec)["v20"],
                             {"위반여부": v20.v20_decision(rec), "근거문구": ""}, rec["id"])


if __name__ == "__main__":
    unittest.main()
