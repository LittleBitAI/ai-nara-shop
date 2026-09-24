"""S7-12 per-item thresholds: P(1) extraction from generated tokens and the threshold step."""

import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = _load("script_under_test", "script.py")
replay_run = _load("replay_run_under_test", "tools/replay_run.py")
lp = math.log


class ItemProbabilitiesTest(unittest.TestCase):
    def test_digit_in_its_own_token(self):
        steps = [('{"v1":{', {}), ('"위반여부":', {}), ("1", {"1": lp(.7), "0": lp(.3)}),
                 (',"근거문구":null}}', {})]
        self.assertAlmostEqual(script.item_probabilities(steps)["v1"], .7)

    def test_digit_merged_with_the_next_character(self):
        steps = [('{"v2":{"위반여부":', {}), ("0,", {"0,": lp(.9), "1,": lp(.1)}), ('"근거문구":null}}', {})]
        self.assertAlmostEqual(script.item_probabilities(steps)["v2"], .1)

    def test_digit_merged_with_the_end_of_the_key(self):
        steps = [('{"v3":{"위반여부', {}), ('":1', {'":1': lp(.6), '":0': lp(.4)}), ('}}', {})]
        self.assertAlmostEqual(script.item_probabilities(steps)["v3"], .6)

    def test_each_item_gets_its_own_digit(self):
        steps = [('{"v1":{"위반여부":', {}), ("0", {"0": lp(.8), "1": lp(.2)}),
                 (',"근거문구":null},"v9":{"위반여부":', {}), ("1", {"1": lp(.55), "0": lp(.45)}), ("}}", {})]
        got = script.item_probabilities(steps)
        self.assertAlmostEqual(got["v1"], .2)
        self.assertAlmostEqual(got["v9"], .55)


class ApplyThresholdsTest(unittest.TestCase):
    def test_empty_thresholds_keep_the_model_answer(self):
        parsed = {"v1": {"위반여부": 1, "근거문구": "a"}}
        self.assertEqual(script.apply_thresholds(dict(parsed), {"v1": .1}, {}), parsed)

    def test_lowering_clears_the_quote_and_missing_probability_is_left_alone(self):
        parsed = {"v1": {"위반여부": 1, "근거문구": "a"}, "v2": {"위반여부": 1, "근거문구": "b"}}
        out = script.apply_thresholds(parsed, {"v1": .6}, {"v1": .9, "v2": .9})
        self.assertEqual(out["v1"], {"위반여부": 0, "근거문구": None})
        self.assertEqual(out["v2"]["위반여부"], 1)

    def test_operating_default_is_empty(self):
        self.assertEqual(script.ITEM_THRESHOLDS, {})


class SavedProbabilitiesTest(unittest.TestCase):
    def test_reads_only_valid_baseline_responses(self):
        events = [{"event": "response", "status": "valid", "phase": "baseline", "id": "A", "item_p1": {"v1": .3}},
                  {"event": "response", "status": "valid", "phase": "sme", "id": "A", "item_p1": {"v13": .9}},
                  {"event": "response", "status": "invalid", "phase": "baseline", "id": "B", "item_p1": {"v1": .5}}]
        with tempfile.TemporaryDirectory() as temporary:
            (Path(temporary) / "diagnostics.jsonl").write_text(
                "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
            self.assertEqual(replay_run.saved_probabilities(temporary), {"A": {"v1": .3}})


if __name__ == "__main__":
    unittest.main()
