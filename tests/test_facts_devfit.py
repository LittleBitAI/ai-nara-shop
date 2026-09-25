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
            "docs": [{"text": "3. 입찰참가자격\n" + text + "\n사. 기타"}]}


class V2Clause(unittest.TestCase):
    def test_fires_under_the_notice_amount_and_quotes_the_line(self):
        self.assertEqual(script.v2_performance_clause(rec(90_000_000)), CLAUSE)

    def test_silent_at_or_above_the_notice_amount(self):
        self.assertIsNone(script.v2_performance_clause(rec(script.NOTICE_AMOUNT_WON)))

    def test_local_small_no_bid_is_the_exception(self):
        self.assertIsNone(script.v2_performance_clause(rec(50_000_000, "지방계약법", "수의계약")))

    def test_performance_outside_the_eligibility_section_is_not_a_clause(self):
        survey = {"meta": {"입찰추정가격": 90_000_000, "적용계약법": "국가계약법", "계약방법": "제한경쟁"},
                  "docs": [{"text": "입찰참가자격: 별도 제한 없음"},
                           {"text": "과업지시서\n시장조사 결과 실적이 있는 업체가 다수였다."}]}
        self.assertIsNone(script.v2_performance_clause(survey))

    def test_a_sibling_section_closes_the_heading(self):
        text = "가. 입찰참가자격: 별도 제한 없음\n나. 과업 개요\n시장조사 결과 실적이 있는 업체가 다수였다."
        survey = {"meta": {"입찰추정가격": 90_000_000, "적용계약법": "국가계약법", "계약방법": "제한경쟁"},
                  "docs": [{"text": text}]}
        self.assertIsNone(script.v2_performance_clause(survey))

    def test_a_description_is_not_a_requirement_even_under_the_heading(self):
        text = "가. 시장조사 결과 실적이 있는 업체가 다수였다."
        self.assertIsNone(script.v2_performance_clause(rec(90_000_000, text=text)))

    def test_a_requirement_ending_in_a_proviso_still_counts(self):
        text = "④ 최근 3년 이내 1억 원 이상 실적이 있는 업체(하도급 제외)"
        self.assertEqual(script.v2_performance_clause(rec(90_000_000, text=text)),
                         "④ 최근 3년 이내 1억 원 이상 실적이 있는 업체")

    def test_a_scoring_table_between_heading_and_clause_blocks_it(self):
        text = "3. 입찰참가자격\n평가 항목 배점표\n" + CLAUSE
        self.assertIsNone(script.v2_performance_clause(rec(90_000_000, text=text)))

    def test_credit_and_performance_boilerplate_is_not_a_clause(self):
        self.assertIsNone(script.v2_performance_clause(rec(90_000_000, text="1) 신용과 실적이 있는 자")))


if __name__ == "__main__":
    unittest.main()
