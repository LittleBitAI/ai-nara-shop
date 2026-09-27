import importlib.util
import json
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("script_slot_rules", ROOT / "script.py")
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)

CLAUSE = "입찰참가자격: 「중소기업기본법」에 따른 소기업 또는 소상공인으로서 확인서를 소지한 업체"


def notice(price, text="입찰참가자격: 나라장터 경쟁입찰참가자격 등록 업체"):
    meta = {"적용계약법": "국가계약법", "계약방법": "제한경쟁", "업무구분": "물품", "입찰추정가격": price}
    return {"id": "T", "docs": [{"doc_id": "D0", "type": "공고문", "text": text}], "meta": meta}


def judgment(**facts):
    base = {"scope": "general", "qualification": "unrestricted", "priority_exception": "no",
            "qualification_quote": None}
    return {script.COMPANY_FACTS_KEY: {**base, **facts}}


def cells(**values):
    return {f"v{i}": {"위반여부": values.get(f"v{i}", 0), "근거문구": ""} for i in range(1, 25)}


class SlotTableTests(unittest.TestCase):
    def decide(self, rec, facts, **values):
        return script.decide_slots(cells(**values), facts, rec)

    def test_all_four_slots_must_hold(self):
        self.assertEqual(self.decide(notice(50_000_000), judgment())["v18"]["위반여부"], 1)
        self.assertEqual(self.decide(notice(150_000_000), judgment())["v18"]["위반여부"], 0)   # not applicable
        self.assertEqual(self.decide(notice(50_000_000), judgment(scope="competitive"))["v18"]["위반여부"], 0)
        self.assertEqual(self.decide(notice(50_000_000), judgment(qualification="unknown"))["v18"]["위반여부"], 0)
        self.assertEqual(self.decide(notice(50_000_000), judgment(priority_exception="yes"))["v18"]["위반여부"], 0)

    def test_no_company_facts_decides_nothing(self):
        # 수의계약 skips the company-size call; the table then leaves every cell as it was.
        self.assertEqual(self.decide(notice(50_000_000), {}, v18=1), cells(v18=1))

    def test_v16_positive_outside_its_band_is_dropped_and_a_size_limit_in_the_text_stops_it(self):
        self.assertEqual(self.decide(notice(300_000_000), judgment(), v16=1)["v16"]["위반여부"], 0)
        self.assertEqual(self.decide(notice(150_000_000), judgment())["v16"]["위반여부"], 1)
        self.assertEqual(self.decide(notice(150_000_000, CLAUSE), judgment())["v16"]["위반여부"], 0)

    def test_v15_needs_its_clause_quoted_from_the_notice(self):
        rec = notice(150_000_000, CLAUSE)
        quoted = self.decide(rec, judgment(qualification="small_only", qualification_quote=CLAUSE))["v15"]
        self.assertEqual(quoted, {"위반여부": 1, "근거문구": CLAUSE})
        invented = self.decide(rec, judgment(qualification="small_only", qualification_quote="소기업만 참가"))
        self.assertEqual(invented["v15"]["위반여부"], 0)


PERFORMANCE = "다. 최근 3년간 단일 계약 건으로 5천만원 이상의 납품 실적이 있는 업체"


def labels(*records):
    base = {"holder": "firm", "size": "na", "region": "na", "orderer": "any", "amount": "won_amount"}
    return json.dumps({"relations": [{**base, **r} for r in records]})


class RelationTests(unittest.TestCase):
    ROW = {"v2": (("under_notice",), ("entry_performance",), (), ("entry_performance",))}

    def setUp(self):
        self.rec = notice(50_000_000, "3. 입찰참가자격\n" + PERFORMANCE)
        clauses, _ = script.clause_candidates(self.rec)
        self.clause_id = next(c["id"] for c in clauses if c["full"] == PERFORMANCE)

    def decide(self, text, **values):
        judgment = {}
        script.attach_relations(judgment, self.rec, text)
        with mock.patch.dict(script.SLOT_RULES, self.ROW):
            return script.decide_slots(cells(**values), judgment, self.rec)["v2"]

    def test_an_entry_performance_label_raises_with_its_own_clause_as_evidence(self):
        text = labels({"id": self.clause_id, "kind": "performance_record", "stage": "entry"})
        self.assertEqual(self.decide(text), {"위반여부": 1, "근거문구": PERFORMANCE})

    def test_the_same_clause_labelled_as_evaluation_lowers_the_main_call_positive(self):
        text = labels({"id": self.clause_id, "kind": "performance_record", "stage": "evaluation"})
        self.assertEqual(self.decide(text, v2=1)["위반여부"], 0)

    def test_no_labels_leaves_the_cell(self):
        self.assertEqual(self.decide(None, v2=1)["위반여부"], 1)
        self.assertEqual(self.decide("not json", v2=1)["위반여부"], 1)

    def test_code_compares_the_required_amount_with_the_price(self):
        text = labels({"id": self.clause_id, "kind": "performance_record", "stage": "entry"})
        for price, one_times in ((40_000_000, True), (50_000_000, True), (90_000_000, False)):   # asks 5천만원
            rec = notice(price, "3. 입찰참가자격\n" + PERFORMANCE)
            judgment = {}
            script.attach_relations(judgment, rec, text)
            self.assertEqual(script.relation_slots(judgment, rec)["entry_performance_budget"], one_times)

    def test_labels_must_use_the_schema_values_and_known_clause_ids(self):
        with self.assertRaises(ValueError):
            script.parse_judgment(labels({"id": 1, "kind": "other", "stage": "entry"}),
                                  expected_items=script.RELATION_KEYS)
        judgment = {}
        script.attach_relations(judgment, self.rec, labels({"id": 79, "kind": "performance_record", "stage": "entry"}))
        self.assertEqual(judgment[script.RELATION_KEY]["relations"], [])

    def test_the_prompt_numbers_the_qualification_clause(self):
        messages, clauses, complete = script.relation_messages(self.rec)
        self.assertIn(f"[{self.clause_id}] {PERFORMANCE}", messages[1]["content"])
        self.assertTrue(complete)


if __name__ == "__main__":
    unittest.main()
