"""D facts call: the decision table and its merge path. No model calls."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import replay_run  # noqa: E402

script = replay_run.load_module(ROOT / "script.py", "submission")

PERF = "최근 3년 이내 단일 건으로 1억원 이상의 유지보수 실적이 있는 업체"
REGION = "본점 소재지가 강원도에 있는 업체"


def rec(price, text=f"입찰참가자격\n{PERF}\n{REGION}\n"):
    return {"id": "T", "docs": [{"doc_id": "D0", "type": "공고문", "text": text}],
            "meta": {"적용계약법": "국가계약법", "업무구분": "일반용역", "계약방법": "제한경쟁",
                     "입찰추정가격": price}}


def facts(**kw):
    return {**script.empty_qualification_facts(), "observed": "yes", "region": "none",
            "performance": "none", "performance_amount": "none", "performance_source": "none",
            "institution": "none", **kw}


class Decide(unittest.TestCase):

    def test_performance_under_notice_amount_is_v2_not_v3(self):
        out = script.decide_qualification(
            facts(performance="eligibility", performance_quote=PERF, performance_amount="below_budget"),
            rec(90_000_000))
        self.assertEqual(out["v2"], {"위반여부": 1, "근거문구": PERF})
        self.assertEqual(out["v3"]["위반여부"], 0)

    def test_price_at_notice_amount_rules_out_v2_whatever_the_facts(self):
        out = script.decide_qualification(facts(performance="eligibility", performance_quote=PERF),
                                          rec(300_000_000))
        self.assertEqual(out["v2"]["위반여부"], 0)

    def test_a_certificate_in_an_operative_clause_is_an_entry_condition(self):
        clause = "입찰참가자격: 최근 3년간 1억원 이상 납품실적증명서를 소지한 자만 입찰 가능"
        out = script.decide_qualification(facts(performance="eligibility", performance_quote=clause),
                                          rec(90_000_000, f"입찰참가자격\n{clause}\n"))
        self.assertEqual(out["v2"]["위반여부"], 1)

    def test_a_checklist_or_evaluation_quote_is_no_entry_condition(self):
        for quote in ("최근 3년간 사업수행 실적 1부", "실적은 평가 점수에만 반영"):
            out = script.decide_qualification(facts(performance="eligibility", performance_quote=quote),
                                              rec(90_000_000, f"입찰참가자격\n{quote}\n"))
            self.assertNotIn("v2", out, quote)

    def test_the_same_clause_counts_when_any_occurrence_is_an_entry_condition(self):
        clause = "최근 3년 이내 단일 건으로 5천만원 이상의 유지보수 실적이 있는 업체"
        text = f"정량평가 배점표\n가. {clause}\n\n입찰참가자격\n나. {clause}\n"
        self.assertTrue(script.in_qualification_section(clause, rec(90_000_000, text)))

    def test_record_at_budget_is_v3(self):
        out = script.decide_qualification(
            facts(performance="eligibility", performance_quote=PERF, performance_amount="at_or_above_budget"),
            rec(90_000_000))
        self.assertEqual(out["v3"]["위반여부"], 1)

    def test_province_only_limit_is_not_v6(self):
        out = script.decide_qualification(facts(region="province", region_quote=REGION), rec(90_000_000))
        self.assertEqual(out["v6"]["위반여부"], 0)
        self.assertEqual(out["v5"]["위반여부"], 0)

    def test_quote_not_in_the_notice_raises_nothing(self):
        out = script.decide_qualification(
            facts(performance="eligibility", performance_quote="지어낸 실적 조항"), rec(90_000_000))
        self.assertNotIn("v2", out)

    def test_unobserved_keeps_the_main_verdict_where_price_does_not_decide(self):
        out = script.decide_qualification(facts(observed="no"), rec(90_000_000))
        self.assertNotIn("v1", out)
        self.assertNotIn("v3", out)
        self.assertNotIn("v8", out)


class V6QuotePlace(unittest.TestCase):

    def test_a_place_bound_to_a_location_keeps_v6_and_a_bare_si_word_does_not(self):
        self.assertTrue(script.v6_quote_names_basic_place("본점 소재지는\n고양시에 있는 업체"))
        self.assertTrue(script.v6_quote_names_basic_place("[지역:r1|단위=기초|광역=경기도] 관내에 소재한 업체"))
        for quote in ("본점 소재지가 강원도에 있는 업체로 제한한다.\n계약체결시 증빙 제출.",
                      "본점 소재지가 서울특별시에 있는 업체, 계약체결시에 제출",
                      "본점 소재지가 대구광역시에 있는 업체"):
            self.assertFalse(script.v6_quote_names_basic_place(quote), quote)

    def test_postprocess_keeps_a_wrapped_city_clause_and_lowers_a_province_one(self):
        def run(quote):
            rec = {"id": "T", "docs": [{"doc_id": "D0", "type": "공고문", "text": "입찰참가자격\n" + quote + "\n"}],
                   "meta": {"적용계약법": "지방계약법", "업무구분": "일반용역", "계약방법": "제한경쟁",
                            "입찰추정가격": 50_000_000}}
            j = {v: {"위반여부": 0, "근거문구": None} for v in script.ITEMS}
            j["v6"] = {"위반여부": 1, "근거문구": quote}
            return script.postprocess(j, rec)["v6"]["위반여부"]
        self.assertEqual(run("본점 소재지는\n고양시에 있는 업체"), 1)
        self.assertEqual(run("본점 소재지가 강원도에 있는 업체로 제한한다.\n계약체결시 증빙 제출."), 0)


class Merge(unittest.TestCase):

    def test_merge_applies_only_listed_items_and_survives_bad_json(self):
        parsed = {v: {"위반여부": 0, "근거문구": None} for v in script.ITEMS}
        text = json.dumps({"qualification_facts": facts(performance="eligibility", performance_quote=PERF)},
                          ensure_ascii=False)
        script.merge_extra_call(parsed, rec(90_000_000), "qualification", ["v2"], text)
        self.assertEqual(parsed["v2"]["위반여부"], 1)
        self.assertEqual(parsed["v8"]["위반여부"], 0)
        script.merge_extra_call(parsed, rec(90_000_000), "qualification", ["v2"], "not json")
        self.assertEqual(parsed["v2"]["위반여부"], 1)


class Deadline(unittest.TestCase):

    def test_past_deadline_the_facts_call_is_skipped_and_the_run_completes(self):
        import tempfile
        saved = script.QUALIFICATION_DEADLINE_S
        script.QUALIFICATION_DEADLINE_S = -1
        try:
            with tempfile.TemporaryDirectory() as tmp:
                report = script.run(str(ROOT / "open/data/test.jsonl.gz"), str(Path(tmp) / "submission.csv"),
                                    script.MockRunner, limit=4, chunk=128, max_chars=16000,
                                    data_dir=str(ROOT / "open/data"))
        finally:
            script.QUALIFICATION_DEADLINE_S = saved
        self.assertGreater(report["qualification_selected_count"], 0)
        self.assertEqual(report["qualification_response_count"], 0)


if __name__ == "__main__":
    unittest.main()
