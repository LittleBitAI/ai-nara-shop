"""C5 분석 도구 검사. 모델을 부르지 않는다.

이 도구는 **회차가 오기 전에** 만들어졌다. 그 말은 처음 쓰는 날 아무도 값을 검산하지
않는다는 뜻이므로, 이미 보관된 회차 두 개를 여기에 걸어 둔다. 셈이 틀어지면 여기서 죽는다.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "reports/team-c/c5-v14-v15/analyze_diagnose.py"
LOOSE = REPO / "reports/runs/colab-1789658250172468461/diagnose/items.jsonl"
CONSERVATIVE = REPO / "reports/runs/colab-1789695980726180378/diagnose/items.jsonl"

_spec = importlib.util.spec_from_file_location("analyze_diagnose", TOOL)
analyze = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(analyze)


def run(path, items):
    """도구를 실제 진입점으로 돌리고 찍힌 것을 돌려준다."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = analyze.main([str(path), "--items", items])
    assert code == 0, f"main() 이 {code} 를 돌려줬다"
    return buffer.getvalue()


class Bands(unittest.TestCase):
    def test_v16_v18_come_from_the_candidate(self):
        """구간 복제본을 두면 후보가 바꿔도 이 도구는 옛 구간으로 답한다."""
        from experiments.sme_candidate import AMOUNT_BANDS
        for item, band in AMOUNT_BANDS.items():
            self.assertEqual(analyze.BANDS[item], band, f"{item} 구간이 후보와 다르다")

    def test_unreadable_amount_does_not_filter(self):
        self.assertTrue(analyze.in_band("v16", None))
        self.assertFalse(analyze.in_band("v16", 50_000_000))
        self.assertTrue(analyze.in_band("v99", 1))   # 구간 없는 항목은 거르지 않는다


class Counts(unittest.TestCase):
    def test_f1_of_a_perfect_and_an_empty_call(self):
        self.assertEqual(analyze.counts([(1, 1), (0, 0)]), {"tp": 1, "fp": 0, "fn": 0, "f1": 1.0})
        self.assertEqual(analyze.counts([(0, 0)])["f1"], 0.0)


class ArchivedRuns(unittest.TestCase):
    """보관 회차 두 개의 값을 건다. 이 도구가 낼 숫자로 다음 결정을 하기 때문이다."""

    def test_loose_run_v16(self):
        if not LOOSE.is_file():
            raise unittest.SkipTest(f"{LOOSE} 가 없다")
        out = run(LOOSE, "v16")
        self.assertIn("TP/FP/FN 6/139/0", out, out)
        self.assertIn("TP/FP/FN 6/39/0", out, out)
        # 이 회차는 `판정` 과 `막힌_단계` 를 따로 채웠다. 조용히 한쪽을 고르면 안 된다.
        self.assertIn("116건 어긋난다", out, out)

    def test_conservative_run_v16(self):
        if not CONSERVATIVE.is_file():
            raise unittest.SkipTest(f"{CONSERVATIVE} 가 없다")
        out = run(CONSERVATIVE, "v16")
        self.assertIn("TP/FP/FN 1/29/5", out, out)
        self.assertIn("TP/FP/FN 1/17/5", out, out)

    def test_unknown_item_is_refused(self):
        if not LOOSE.is_file():
            raise unittest.SkipTest(f"{LOOSE} 가 없다")
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            self.assertEqual(analyze.main([str(LOOSE), "--items", "v99"]), 1)
        self.assertIn("v99", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
