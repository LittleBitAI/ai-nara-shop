"""Facts dev-fit: the v2 past-performance clause detector."""

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("script_under_test", ROOT / "script.py")
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)

CLAUSE = "바. 최근 10년 이내 5천만원 이상 디자인 용역 수행 실적이 있는 자"


def rec(price, law="국가계약법", method="제한경쟁", text=CLAUSE):
    return {"meta": {"입찰추정가격": price, "적용계약법": law, "계약방법": method},
            "docs": [{"text": "가. 입찰참가자격\n" + text + "\n사. 기타"}]}


class V2Clause(unittest.TestCase):
    def test_fires_under_the_notice_amount_and_quotes_the_line(self):
        self.assertEqual(script.v2_performance_clause(rec(90_000_000)), CLAUSE)

    def test_silent_at_or_above_the_notice_amount(self):
        self.assertIsNone(script.v2_performance_clause(rec(script.NOTICE_AMOUNT_WON)))

    def test_local_small_no_bid_is_the_exception(self):
        self.assertIsNone(script.v2_performance_clause(rec(50_000_000, "지방계약법", "수의계약")))

    def test_credit_and_performance_boilerplate_is_not_a_clause(self):
        self.assertIsNone(script.v2_performance_clause(rec(90_000_000, text="1) 신용과 실적이 있는 자")))


if __name__ == "__main__":
    unittest.main()
