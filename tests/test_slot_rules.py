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
    ROW = {"v2": (("under_notice",), ("entry_performance",), (), None)}   # no keep-if: the row owns the cell

    def setUp(self):
        self.rec = dict(notice(50_000_000, "3. 입찰참가자격\n" + PERFORMANCE),
                        input_completeness={"완전관측": True}, dropped_doc_counts={})
        clauses, _ = script.clause_candidates(self.rec)
        self.clause_id = next(c["id"] for c in clauses if c["full"] == PERFORMANCE)

    def decide(self, text, rec=None, row=None, item="v2", evidence="", facts=None, **values):
        rec, judgment = rec or self.rec, dict(facts or {})
        script.attach_relations(judgment, rec, text)
        out = cells(**values)
        out[item]["근거문구"] = evidence
        with mock.patch.dict(script.SLOT_RULES, row or self.ROW):
            return script.decide_slots(out, judgment, rec)[item]

    def test_an_entry_performance_label_raises_with_its_own_clause_as_evidence(self):
        text = labels({"id": self.clause_id, "kind": "performance_record", "stage": "entry"})
        self.assertEqual(self.decide(text), {"위반여부": 1, "근거문구": PERFORMANCE})

    def test_the_same_clause_labelled_as_evaluation_lowers_the_main_call_positive(self):
        text = labels({"id": self.clause_id, "kind": "performance_record", "stage": "evaluation"})
        self.assertEqual(self.decide(text, evidence=PERFORMANCE, v2=1)["위반여부"], 0)

    def test_no_labels_leaves_the_cell(self):
        self.assertEqual(self.decide(None, v2=1)["위반여부"], 1)
        self.assertEqual(self.decide("not json", v2=1)["위반여부"], 1)

    def test_the_amount_is_compared_as_the_v3_deletion_rule_compares_it(self):
        text = labels({"id": self.clause_id, "kind": "performance_record", "stage": "entry"})
        for price, budget in ((40_000_000, None), (50_000_000, None), (90_000_000, None),
                              (40_000_000, 60_000_000), (60_000_000, 40_000_000)):   # the clause asks 5천만원
            rec = notice(price, "3. 입찰참가자격\n" + PERFORMANCE)
            if budget:
                rec["meta"]["배정예산금액"] = budget
            judgment = {}
            script.attach_relations(judgment, rec, text)
            self.assertEqual(script.relation_slots(judgment, rec)["entry_performance_budget"],
                             not script._below_budget(PERFORMANCE, rec), (price, budget))

    def test_a_missing_label_lowers_only_a_positive_whose_cited_clause_was_read(self):
        nothing = labels()
        self.assertEqual(self.decide(nothing, evidence=PERFORMANCE, v2=1)["위반여부"], 0)
        self.assertEqual(self.decide(nothing, evidence="다른 문서의 실적 조항", v2=1)["위반여부"], 1)
        self.assertEqual(self.decide(nothing, v2=1)["위반여부"], 1)                    # no evidence: unknown
        full = [{"id": self.clause_id, "kind": "performance_record", "stage": "evaluation"}] * script.RELATION_MAX
        self.assertEqual(self.decide(labels(*full), evidence=PERFORMANCE, v2=1)["위반여부"], 1)   # at the cap

    def test_a_wrapped_line_is_one_clause_and_its_evidence_is_the_exact_span(self):
        wrapped = ("2) 전자입찰서 제출 마감일 전일까지 입찰참가 등록한 업체\n"
                   "※ 제조업체가 아닐 경우 물품계약 시 제조업체로부터 “제조자의 공급\n"
                   "확약서 및 기술지원 A/S확약서”를 제출할 수 있는 업체\n"
                   "3) 농업용기계 제조업으로 사업자등록을 필한 업체")
        rec = notice(50_000_000, "3. 입찰참가자격\n" + wrapped)
        clauses, _ = script.clause_candidates(rec)
        pledge = next(c for c in clauses if "확약서" in c["text"])
        self.assertIn("물품계약 시", pledge["text"])
        self.assertIn("\n", pledge["full"])
        self.assertEqual(script.clean_evidence(pledge["full"], rec["docs"][0]["text"]), pledge["full"])
        self.assertEqual(len([c for c in clauses if c["text"].startswith(("2)", "※", "3)"))]), 3)

    def test_a_missing_label_never_raises_an_absence(self):
        absence = {"v10": ((), ("!entry_direct_production",), (), None)}
        self.assertEqual(self.decide(labels(), row=absence, item="v10")["위반여부"], 0)
        self.assertEqual(self.decide(labels(), row=absence, item="v10", v10=1)["위반여부"], 1)

    def test_an_unknown_scope_or_region_never_raises(self):
        location = labels({"id": self.clause_id, "kind": "bidder_location", "stage": "entry", "region": "basic"})
        goods = dict(self.rec["meta"], 업무구분="물품(내자)")                     # limit 2.3억 (국가계약법)
        for item, applies, price in (("v6", "region_allowed", 50_000_000), ("v5", "over_region_limit", 900_000_000)):
            row = {item: ((applies,), ("entry_location",), (), None)}
            known = dict(self.rec, meta=dict(goods, 입찰추정가격=price))
            self.assertEqual(self.decide(location, rec=known, row=row, item=item)["위반여부"], 1, item)
            unpriced = dict(self.rec, meta=dict(goods, 입찰추정가격=None, 배정예산금액=price))
            self.assertEqual(self.decide(location, rec=unpriced, row=row, item=item)["위반여부"], 0, item)
        production = labels({"id": self.clause_id, "kind": "direct_production", "stage": "entry"})
        row = {"v12": (("!catalogue_product",), ("entry_direct_production",), (), None)}
        self.assertEqual(self.decide(production, row=row, item="v12")["위반여부"], 0)   # no product code
        row = {"v12": (("scope_general",), ("entry_direct_production",), (), None)}
        self.assertEqual(self.decide(production, row=row, item="v12", facts=judgment())["위반여부"], 1)

    def test_a_known_exception_decides_on_its_own(self):
        row = {"v17": (("small",), ("entry_sme",), ("priority_exception",), None)}
        facts = judgment(priority_exception="yes")
        self.assertEqual(self.decide(labels(), row=row, item="v17", facts=facts, v17=1)["위반여부"], 0)
        facts = judgment(priority_exception="unknown")
        self.assertEqual(self.decide(labels(), row=row, item="v17", facts=facts, v17=1)["위반여부"], 1)

    def test_a_known_scope_failure_decides_even_when_the_labels_say_nothing(self):
        row = {"v4": (("over_notice",), ("entry_performance_institution",), (), None)}
        self.assertEqual(self.decide(labels(), row=row, item="v4", v4=1)["위반여부"], 0)    # 5천만원: under
        unpriced = dict(self.rec, meta=dict(self.rec["meta"], 입찰추정가격=None))
        self.assertEqual(self.decide(labels(), rec=unpriced, row=row, item="v4", v4=1)["위반여부"], 1)

    def test_negotiation_is_read_from_the_award_method_as_v22_reads_it(self):
        rec = dict(self.rec, meta=dict(self.rec["meta"], 계약방법="제한경쟁", 낙찰방법="협상에의한계약"))
        self.assertTrue(script.relation_slots({}, rec)["negotiation"])
        self.assertEqual(script.negotiated(rec), script.relation_slots({}, rec)["negotiation"])

    def test_no_relation_call_starts_after_the_deadline(self):
        runner = mock.Mock()
        runner.chat.return_value = ["not json"]
        runner.last_response_info = []
        valid = json.dumps({f"v{i}": {"위반여부": 0, "근거문구": ""} for i in range(1, 25)})
        call = dict(items=script.RELATION_KEYS, phase="relation", baseline_texts=[valid], indices=[0])
        batch = [[{"role": "user", "content": "x"}]]
        self.assertEqual(script.run_chunk(runner, batch, deadline=0.0, **call), [None])
        runner.chat.assert_not_called()
        # The first call ran; its failed response is not retried once the deadline has passed.
        with mock.patch.object(script.time, "time", side_effect=[0.0, 2.0]):
            self.assertEqual(script.run_chunk(runner, batch, deadline=1.0, **call), [None])
        runner.chat.assert_called_once()
        runner.retry_chat.assert_not_called()

    def test_every_fit_candidate_stays_inside_its_item_scope(self):
        spec = importlib.util.spec_from_file_location("relation_fit", ROOT / "reports/relation-pipeline/fit.py")
        fit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fit)                 # the scope invariant is asserted on import
        self.assertNotIn((), fit.GENERAL)

    def test_a_cut_clause_is_not_complete(self):
        filler = "가" * script.CLAUSE_TEXT_MAX
        for heading in ("3. 입찰참가자격", "1. 기타사항"):   # a weak-trigger clause's tail counts too
            long = "가. 입찰참가자격 " + filler + " 직생 확인서를 제출해야 함"
            clauses, complete = script.clause_candidates(notice(50_000_000, heading + "\n" + long))
            self.assertFalse(complete, heading)
            self.assertNotIn("직생", clauses[0]["text"])

    def test_a_list_heading_reaches_the_clauses_under_it(self):
        text = ("4. 입찰자격 조건\n가. 자격 조건\n1) 제조사로부터 물품공급 확약서를 제출할 수 있는 업체\n"
                "나. 계약 시 제출서류\n1) 물품 제조사와 체결한 물품공급 확약서 원본 1부")
        messages, clauses, _ = script.relation_messages(notice(50_000_000, text))
        self.assertEqual([c["section"] for c in clauses if "확약서" in c["text"]],
                         ["4. 입찰자격 조건 › 가. 자격 조건", "4. 입찰자격 조건 › 나. 계약 시 제출서류"])
        self.assertIn("나. 계약 시 제출서류", messages[1]["content"])

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
