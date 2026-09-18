"""참가자격 제한 4항목(v8·v7·v4·v3) 후보 검사. 모델을 부르지 않는다. live 성능 검사가 아니다."""

import csv
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "qualification_candidate", ROOT / "experiments" / "qualification_candidate.py")
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)

DEV = ROOT / "open" / "dev.jsonl"
LABELS = ROOT / "open" / "dev_labels.csv"

# 실제 dev 정답의 항목별 양성 전수. 여기서 하나라도 빠지면 후보가 후퇴한 것이다.
POSITIVES = ["PPS-DEV-05", "PPS-DEV-11", "PPS-DEV-042",
             "PPS-DEV-048", "PPS-DEV-054", "PPS-DEV-071"]
V7_POSITIVES = ["PPS-DEV-09", "PPS-DEV-10", "PPS-DEV-039",
                "PPS-DEV-050", "PPS-DEV-054", "PPS-DEV-063", "PPS-DEV-072"]
V4_POSITIVES = ["PPS-DEV-06", "PPS-DEV-042", "PPS-DEV-051",
                "PPS-DEV-053", "PPS-DEV-059", "PPS-DEV-062"]


def load_dev():
    return {json.loads(line)["id"]: json.loads(line)
            for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()}


def load_truth(item="v8"):
    with LABELS.open(encoding="utf-8", newline="") as stream:
        return {row["id"]: row[item] == "1" for row in csv.DictReader(stream)}


def notice(text):
    return {"id": "sample", "docs": [{"doc_id": "a", "type": "공고문", "text": text}],
            "meta": {"지역제한여부": None}}


def empty_judgment():
    return {f"v{i}": {"위반여부": 0, "근거문구": None} for i in range(1, 25)}


class DevCoverage(unittest.TestCase):
    """공개 dev 200건 전수. 표본이 아니라 전부를 돌린다."""

    @classmethod
    def setUpClass(cls):
        cls.recs = load_dev()
        cls.truth = load_truth()

    def test_dev_positive_ids_match_the_label_file(self):
        actual = sorted(i for i, gold in self.truth.items() if gold)
        self.assertEqual(sorted(POSITIVES), actual)

    def test_every_positive_is_detected_with_a_real_clause(self):
        for rec_id in POSITIVES:
            with self.subTest(rec_id):
                hit = candidate.detect(self.recs[rec_id])
                self.assertIsNotNone(hit, "양성인데 검출되지 않았다")
                # 우연히 맞는 것을 막는다. 두 요건이 같은 문서에서 창 안에 있어야 한다.
                self.assertLessEqual(hit["distance"], candidate.WINDOW)
                self.assertTrue(hit["performance"].strip())
                self.assertTrue(hit["region"].strip())

    def test_no_false_positive_on_the_194_negatives(self):
        fired = [i for i, rec in self.recs.items()
                 if not self.truth[i] and candidate.detect(rec)]
        self.assertEqual([], fired, f"음성에서 발화했다: {fired}")

    def test_evidence_is_a_contiguous_quotation_from_a_supplied_document(self):
        for rec_id in POSITIVES:
            with self.subTest(rec_id):
                rec = self.recs[rec_id]
                quote = candidate.detect(rec)["근거문구"]
                self.assertLessEqual(len(quote), candidate.QUOTE_MAX)
                self.assertTrue(any(quote in doc["text"] for doc in rec["docs"]),
                                "근거문구가 제공 문서의 부분문자열이 아니다")

    def test_meta_region_flag_alone_would_have_missed_half_the_positives(self):
        """메타로 거르면 안 된다는 것을 데이터로 고정한다."""
        flagged_n = [i for i in POSITIVES if self.recs[i]["meta"]["지역제한여부"] == "N"]
        self.assertEqual(["PPS-DEV-11", "PPS-DEV-048", "PPS-DEV-071"], flagged_n)


class RegionExpansionCoverage(unittest.TestCase):
    """v7 지역제한 인접 확대. dev 200건 전수."""

    @classmethod
    def setUpClass(cls):
        cls.recs = load_dev()
        cls.truth = load_truth("v7")

    def test_dev_positive_ids_match_the_label_file(self):
        self.assertEqual(sorted(V7_POSITIVES),
                         sorted(i for i, gold in self.truth.items() if gold))

    def test_every_positive_names_two_distinct_wide_regions(self):
        for rec_id in V7_POSITIVES:
            with self.subTest(rec_id):
                hit = candidate.detect_region_expansion(self.recs[rec_id])
                self.assertIsNotNone(hit, "양성인데 검출되지 않았다")
                first, second = hit["regions"]
                self.assertNotEqual(first, second, "같은 지역을 두 번 센다")

    def test_no_false_positive_on_the_negatives(self):
        fired = [i for i, rec in self.recs.items()
                 if not self.truth[i] and candidate.detect_region_expansion(rec)]
        self.assertEqual([], fired, f"음성에서 발화했다: {fired}")

    def test_evidence_is_a_contiguous_quotation(self):
        for rec_id in V7_POSITIVES:
            with self.subTest(rec_id):
                rec = self.recs[rec_id]
                quote = candidate.detect_region_expansion(rec)["근거문구"]
                self.assertLessEqual(len(quote), candidate.QUOTE_MAX)
                self.assertTrue(any(quote in doc["text"] for doc in rec["docs"]))

    def test_every_positive_is_below_the_price_limit(self):
        """항목명의 `고시금액 미만`. 게이트가 정답 양성을 막지 않아야 한다."""
        for rec_id in V7_POSITIVES:
            with self.subTest(rec_id):
                self.assertTrue(candidate.region_restriction_allowed(self.recs[rec_id]))

    def test_v5_positives_are_above_the_price_limit(self):
        """고시금액 이상 지역제한은 v5의 몫이다. 경계가 두 항목을 실제로 가르는지 본다."""
        truth_v5 = load_truth("v5")
        for rec_id, gold in truth_v5.items():
            if gold:
                with self.subTest(rec_id):
                    self.assertFalse(candidate.region_restriction_allowed(self.recs[rec_id]))

    def test_price_at_or_above_the_limit_suppresses_the_rule(self):
        text = ("입찰참가자격 본점 소재지를 경기도 또는 서울특별시의 관할구역 안에 둔 업체")
        for law, price in (("국가계약법", 230_000_000), ("지방계약법", 500_000_000)):
            with self.subTest(law):
                rec = notice(text)
                rec["meta"].update({"적용계약법": law, "업무구분": "일반용역",
                                    "입찰추정가격": price})
                self.assertIsNone(candidate.detect_region_expansion(rec))
                rec["meta"]["입찰추정가격"] = price - 1
                self.assertIsNotNone(candidate.detect_region_expansion(rec))

    def test_unknown_price_or_scope_does_not_suppress(self):
        """금액·업무구분을 모르면 막지 않는다. 막는 쪽이 틀리면 양성을 잃는다."""
        text = "입찰참가자격 본점 소재지를 경기도 또는 서울특별시의 관할구역 안에 둔 업체"
        for meta in ({"적용계약법": "국가계약법", "업무구분": "일반용역", "입찰추정가격": None},
                     {"적용계약법": None, "업무구분": "일반용역", "입찰추정가격": 900_000_000},
                     {"적용계약법": "지방계약법", "업무구분": "공사", "입찰추정가격": 900_000_000}):
            with self.subTest(str(meta)):
                rec = notice(text)
                rec["meta"].update(meta)
                self.assertTrue(candidate.region_restriction_allowed(rec))
                self.assertIsNotNone(candidate.detect_region_expansion(rec))


class InstitutionPerformanceCoverage(unittest.TestCase):
    """v4 특정기관·특정실적. dev 200건 전수."""

    @classmethod
    def setUpClass(cls):
        cls.recs = load_dev()
        cls.truth = load_truth("v4")

    def test_dev_positive_ids_match_the_label_file(self):
        self.assertEqual(sorted(V4_POSITIVES),
                         sorted(i for i, gold in self.truth.items() if gold))

    def test_every_positive_is_detected(self):
        for rec_id in V4_POSITIVES:
            with self.subTest(rec_id):
                self.assertIsNotNone(candidate.detect_institution_performance(self.recs[rec_id]))

    def test_no_false_positive_on_the_negatives(self):
        fired = [i for i, rec in self.recs.items()
                 if not self.truth[i] and candidate.detect_institution_performance(rec)]
        self.assertEqual([], fired, f"음성에서 발화했다: {fired}")

    def test_amount_is_not_used_as_a_gate(self):
        """금액 기준을 걸면 안 된다는 것을 데이터로 고정한다."""
        prices = sorted(self.recs[i]["meta"]["입찰추정가격"] for i in V4_POSITIVES)
        self.assertLess(prices[0], 220_000_000, "양성 최저가가 고시금액 근처보다 낮다")
        self.assertGreater(prices[-1], 220_000_000, "양성 최고가가 고시금액 근처보다 높다")


class ExcessPerformanceGuard(unittest.TestCase):
    """v3 실적제한 1배수 이상. 이 규칙만 1을 0으로 내리므로 TP 보존을 먼저 지킨다."""

    @classmethod
    def setUpClass(cls):
        cls.recs = load_dev()
        cls.truth = load_truth("v3")

    def test_no_true_positive_is_downgraded(self):
        """v3 TP 8건을 하나라도 잃으면 이 후보는 반려다."""
        lost = [i for i, rec in self.recs.items()
                if self.truth[i] and candidate.performance_below_budget(rec) is not None]
        self.assertEqual([], lost, f"정답 양성을 내렸다: {lost}")

    def test_known_false_positives_are_downgraded(self):
        """예산 1배에 못 미치는 것이 실제로 읽힌 오탐."""
        for rec_id, ceiling in (("PPS-DEV-06", 0.6), ("PPS-DEV-054", 0.4),
                                ("PPS-DEV-069", 0.7), ("PPS-DEV-141", 0.3)):
            with self.subTest(rec_id):
                ratio = candidate.performance_below_budget(self.recs[rec_id])
                self.assertIsNotNone(ratio, "배수를 읽지 못했다")
                self.assertLess(ratio, ceiling)

    def test_unreadable_amount_leaves_the_model_alone(self):
        """금액을 못 읽으면 내리지 않는다. 모르는 것을 근거로 삼지 않는다."""
        rec = notice("입찰참가자격 유사 용역 수행 실적이 있는 업체")
        rec["meta"]["입찰추정가격"] = 100_000_000
        self.assertIsNone(candidate.required_performance(rec))
        self.assertIsNone(candidate.performance_below_budget(rec))

    def test_missing_basis_leaves_the_model_alone(self):
        rec = notice("입찰참가자격 최근 3년 이내 1억원 이상의 실적을 보유한 업체")
        rec["meta"]["입찰추정가격"] = None
        rec["meta"]["배정예산금액"] = None
        self.assertIsNone(candidate.performance_below_budget(rec))

    def test_estimated_price_is_the_basis_and_budget_is_the_fallback(self):
        """조문 기준은 추정가격이다. 없을 때만 예산으로 물러선다."""
        rec = notice("입찰참가자격 최근 3년 이내 1억원 이상의 실적을 보유한 업체")
        rec["meta"]["입찰추정가격"] = 300_000_000
        rec["meta"]["배정예산금액"] = 50_000_000
        self.assertIsNotNone(candidate.performance_below_budget(rec))
        rec["meta"]["입찰추정가격"] = None
        self.assertIsNone(candidate.performance_below_budget(rec))

    def test_at_or_above_one_times_budget_is_kept(self):
        rec = notice("입찰참가자격 최근 3년 이내 3억원 이상의 실적을 보유한 업체")
        rec["meta"]["입찰추정가격"] = 250_000_000
        self.assertIsNone(candidate.performance_below_budget(rec))

    def test_korean_amount_units_are_read(self):
        for text, expected in (("1억원 이상의 실적", 100_000_000),
                               ("5천만원 이상의 실적", 50_000_000),
                               ("3,000만원 이상 실적", 30_000_000)):
            with self.subTest(text):
                self.assertEqual(expected, candidate.required_performance(notice(text)))

    def test_scoring_table_amounts_are_not_used(self):
        rec = notice("제안서 평가 배점 유사 용역 수행실적 10억원 이상 5점")
        self.assertIsNone(candidate.required_performance(rec))


class CounterExamples(unittest.TestCase):
    """실적만·지역만·가점만 있는 공고는 중복제한이 아니다."""

    def test_performance_requirement_alone_does_not_fire(self):
        text = "입찰참가자격 가. 최근 3년 이내 단일 계약 1억원 이상의 실적을 보유한 업체"
        self.assertIsNone(candidate.detect(notice(text)))

    def test_region_requirement_alone_does_not_fire(self):
        text = "입찰참가자격 가. 입찰공고일 전일까지 주된 영업소의 소재지를 경상남도 내에 둔 사업자"
        self.assertIsNone(candidate.detect(notice(text)))

    def test_scoring_bonus_alone_does_not_fire(self):
        text = ("제안서 평가배점 - 지역업체 참여도 5점 - 유사 용역 수행 건수 10점 "
                "※ 위 항목은 평가 배점이며 입찰참가자격을 제한하지 않는다")
        self.assertIsNone(candidate.detect(notice(text)))

    def test_two_requirements_far_apart_do_not_fire(self):
        text = ("주된 영업소가 서울특별시 관내에 있는 업체" + "가" * (candidate.WINDOW + 200)
                + "최근 3년 이내 1억원 이상의 실적을 보유한 업체")
        self.assertIsNone(candidate.detect(notice(text)))

    def test_single_region_restriction_is_not_an_expansion(self):
        text = "입찰참가자격 주된 영업소의 소재지를 경상남도 내에 둔 사업자로 제한한다"
        self.assertIsNone(candidate.detect_region_expansion(notice(text)))

    def test_same_region_named_twice_is_not_an_expansion(self):
        text = ("입찰참가자격 본점 소재지가 경기도에 있고 경기도 내 시설을 보유한 업체")
        self.assertIsNone(candidate.detect_region_expansion(notice(text)))

    def test_performance_open_to_private_clients_is_not_v4(self):
        text = ("입찰참가자격 최근 5년간 국가, 지방자치단체, 공공기관, 민간에서 시행한 "
                "행사 실적이 1억원 이상 있는 업체이어야 합니다")
        self.assertIsNone(candidate.detect_institution_performance(notice(text)))

    def test_institution_performance_in_a_scoring_table_is_not_v4(self):
        text = ("제안서 평가 배점 - 유사사업 수행실적(5점) 최근 5년간 국가·지자체 및 "
                "공공기관에서 발주한 용역 참여 실적 1건당 1점 배점")
        self.assertIsNone(candidate.detect_institution_performance(notice(text)))

    def test_institution_performance_in_a_submission_form_is_not_v4(self):
        text = ("【서식 11】 연구용역 수행실적 ※ 범위 : 최근 5년간 국가, 지방자치단체, "
                "공공기관 등에서 발주한 유사용역 수행실적으로 3천만원 이상 단일계약건")
        self.assertIsNone(candidate.detect_institution_performance(notice(text)))

    def test_requirements_in_different_documents_do_not_fire(self):
        rec = {"id": "sample", "meta": {},
               "docs": [{"doc_id": "a", "type": "공고문",
                         "text": "참가자격 주된 영업소가 서울특별시 관내에 있는 업체"},
                        {"doc_id": "b", "type": "과업지시서",
                         "text": "최근 3년 이내 1억원 이상의 실적을 보유한 업체"}]}
        self.assertIsNone(candidate.detect(rec))


class ApplyContract(unittest.TestCase):
    def test_only_the_owned_items_can_change(self):
        owned = set(candidate.ITEMS) | {"v3"}
        recs = load_dev()
        for rec_id in set(POSITIVES + V7_POSITIVES + V4_POSITIVES):
            with self.subTest(rec_id):
                before = empty_judgment()
                after = candidate.apply(before, recs[rec_id])
                for item in after:
                    if item not in owned:
                        self.assertEqual(before[item], after[item],
                                         f"{item}이 담당 밖인데 바뀌었다")

    def test_v3_is_only_lowered_never_raised(self):
        """v3 규칙은 내리기만 한다. 0을 1로 올리지 않는다."""
        recs = load_dev()
        for rec_id in ("PPS-DEV-06", "PPS-DEV-054", "PPS-DEV-05"):
            with self.subTest(rec_id):
                after = candidate.apply(empty_judgment(), recs[rec_id])
                self.assertEqual(0, after["v3"]["위반여부"])

    def test_v3_positive_is_lowered_when_the_amount_falls_short(self):
        recs = load_dev()
        before = empty_judgment()
        before["v3"] = {"위반여부": 1, "근거문구": "모델이 고른 문구"}
        after = candidate.apply(before, recs["PPS-DEV-06"])
        self.assertEqual(0, after["v3"]["위반여부"])
        self.assertIsNone(after["v3"]["근거문구"])

    def test_each_rule_marks_its_own_item(self):
        recs = load_dev()
        for item, rec_id in (("v8", "PPS-DEV-11"), ("v7", "PPS-DEV-09"), ("v4", "PPS-DEV-06")):
            with self.subTest(item):
                after = candidate.apply(empty_judgment(), recs[rec_id])
                self.assertEqual(1, after[item]["위반여부"])

    def test_model_positive_is_kept_untouched(self):
        rec = load_dev()["PPS-DEV-11"]
        before = empty_judgment()
        before["v8"] = {"위반여부": 1, "근거문구": "모델이 고른 문구"}
        self.assertEqual(before["v8"], candidate.apply(before, rec)["v8"])

    def test_v8_v7_v4_never_lower_a_model_positive(self):
        rec = notice("이 공고에는 아무 제한도 없다")
        before = empty_judgment()
        for item in candidate.ITEMS:
            before[item] = {"위반여부": 1, "근거문구": "모델이 고른 문구"}
        after = candidate.apply(before, rec)
        for item in candidate.ITEMS:
            with self.subTest(item):
                self.assertEqual(before[item], after[item])

    def test_input_is_not_mutated(self):
        rec = load_dev()["PPS-DEV-11"]
        before = empty_judgment()
        snapshot = json.dumps(before, ensure_ascii=False, sort_keys=True)
        candidate.apply(before, rec)
        self.assertEqual(snapshot, json.dumps(before, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
