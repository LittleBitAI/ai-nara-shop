"""B10: a v21 positive survives only on a quoted share. The operating code decides the rest."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("b10", ROOT / "experiments/b10_v21_quote_share_candidate.py")
b10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b10)
REAL = b10.baseline()


def stub(quote):
    """A submission module whose postprocess leaves v21=1 with the given quote."""
    module = types.SimpleNamespace(V21_PERCENT=REAL.V21_PERCENT)
    module.postprocess = lambda judgment, rec: {"v21": {"위반여부": 1, "근거문구": quote},
                                                "v1": {"위반여부": 1, "근거문구": "x"}}
    return module


class QuoteShareTest(unittest.TestCase):
    def run_with(self, quote):
        sys.modules["submission"] = stub(quote)
        try:
            return b10.postprocess({}, {})
        finally:
            del sys.modules["submission"]

    def test_quote_without_a_share_is_lowered(self):
        for quote in ("공동수급이 허용되지 않습니다.", "공동계약 : 미허용", "대표사 포함 2개사 이하로 함.", ""):
            with self.subTest(quote=quote):
                self.assertEqual(self.run_with(quote)["v21"], {"위반여부": 0, "근거문구": ""})

    def test_quote_with_a_share_is_left_to_the_operating_rule(self):
        out = self.run_with("구성원별 최소 지분율은 0.5% 이상으로 하여야 함")
        self.assertEqual(out["v21"]["위반여부"], 1)

    def test_other_items_are_untouched(self):
        self.assertEqual(self.run_with("공동수급 불허")["v1"], {"위반여부": 1, "근거문구": "x"})


verdict_spec = importlib.util.spec_from_file_location("b10v", ROOT / "experiments/b10_v21_facts_verdict.py")
b10v = importlib.util.module_from_spec(verdict_spec)
verdict_spec.loader.exec_module(b10v)
LOCAL = {"meta": {"적용계약법": "지방계약법"}}
NATIONAL = {"meta": {"적용계약법": "국가계약법"}}


class FactsVerdictTest(unittest.TestCase):
    """The labeler reads facts; the floor is the operating table (local 5, national 10)."""

    def facts(self, **kw):
        return {"joint_contract": "allowed", "method": "공동이행", "min_share_percent": None,
                "quote": None, "정보부족": False, **kw}

    def test_floor_by_contract_law(self):
        self.assertEqual(b10v.verdict(self.facts(min_share_percent=4), LOCAL), 1)
        self.assertEqual(b10v.verdict(self.facts(min_share_percent=5), LOCAL), 0)
        self.assertEqual(b10v.verdict(self.facts(min_share_percent=5), NATIONAL), 1)

    def test_no_share_barred_or_split_is_not_a_violation(self):
        self.assertEqual(b10v.verdict(self.facts(), LOCAL), 0)
        self.assertEqual(b10v.verdict(self.facts(joint_contract="barred", min_share_percent=2), LOCAL), 0)
        self.assertEqual(b10v.verdict(self.facts(method="분담이행", min_share_percent=2), LOCAL), 0)

    def test_unobservable_counts_against_adoption(self):
        self.assertEqual(b10v.verdict(self.facts(정보부족=True), LOCAL), 1)


if __name__ == "__main__":
    unittest.main()
