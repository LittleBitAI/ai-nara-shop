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
                     {"적용계약법": "지방계약법", "업무구분": "알 수 없음",
                      "입찰추정가격": 900_000_000}):
            with self.subTest(str(meta)):
                rec = notice(text)
                rec["meta"].update(meta)
                self.assertTrue(candidate.region_restriction_allowed(rec))
                self.assertIsNotNone(candidate.detect_region_expansion(rec))

    def test_construction_uses_its_own_limit_and_the_wide_branch(self):
        """공사는 조문이 다른 금액을 둔다. 종합·전문을 메타로 못 가르므로 넓은 쪽을 쓴다.

        이 선택의 결과가 10억~150억 구간의 전문공사를 못 막는 것이고, 그것을
        고르는 이유는 좁은 쪽이 틀리면 종합공사의 정답 양성을 잃기 때문이다.
        """
        text = "입찰참가자격 본점 소재지를 경기도 또는 서울특별시의 관할구역 안에 둔 업체"
        for law, limit in (("국가계약법", 8_800_000_000), ("지방계약법", 15_000_000_000)):
            with self.subTest(law):
                rec = notice(text)
                rec["meta"].update({"적용계약법": law, "업무구분": "공사",
                                    "입찰추정가격": limit})
                self.assertIsNone(candidate.detect_region_expansion(rec))
                rec["meta"]["입찰추정가격"] = limit - 1
                self.assertIsNotNone(candidate.detect_region_expansion(rec))
                # 문서로 남긴 결과: 전문공사 10억 기준은 이 게이트가 막지 못한다.
                rec["meta"]["입찰추정가격"] = 5_000_000_000
                self.assertTrue(candidate.region_restriction_allowed(rec))


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

    def test_composite_amounts_are_summed_not_split(self):
        """`1억 5천만원`을 자리마다 따로 읽고 최댓값을 고르면 1억으로 33% 낮게 읽는다.

        그 값이 1배 경계를 넘나들면 정답 양성을 내려 버린다. 이 표기는 dev 코퍼스에
        이미 있다(PPS-DEV-063·PPS-DEV-076).
        """
        for text, expected in (("1억 5천만원 이상의 실적", 150_000_000),
                               ("2억 3천만원 이상의 실적", 230_000_000),
                               ("1억 5천만 원 이상 실적", 150_000_000),
                               ("금169,521,600원 이상의 실적", 169_521_600),
                               ("3억 이상의 실적", 300_000_000)):
            with self.subTest(text):
                self.assertEqual(expected, candidate.required_performance(notice(text)))

    def test_bare_digit_runs_are_not_money(self):
        """세부품명번호 10자리와 날짜를 금액으로 읽지 않는다."""
        for text in ("세부품명번호 10자리 4321150102 로 등록한 업체의 실적",
                     "2026. 3. 18. 까지 실적 제출"):
            with self.subTest(text):
                self.assertIsNone(candidate.required_performance(notice(text)))

    def test_composite_amount_does_not_downgrade_a_true_positive(self):
        """리뷰가 낸 시나리오. 1억 5천만을 1억으로 읽으면 v3 TP를 잃는다."""
        rec = notice("입찰참가자격 최근 3년 이내 1억 5천만원 이상의 실적을 보유한 업체")
        rec["meta"]["입찰추정가격"] = 120_000_000
        self.assertEqual(150_000_000, candidate.required_performance(rec))
        self.assertIsNone(candidate.performance_below_budget(rec))

    def test_scoring_table_amounts_are_not_used(self):
        rec = notice("제안서 평가 배점 유사 용역 수행실적 10억원 이상 5점")
        self.assertIsNone(candidate.required_performance(rec))


class RecordedHashes(unittest.TestCase):
    """보고서가 인용하는 해시가 실제 파일과 같은지.

    PR #34 리뷰에서 후보 코드 해시가 어떤 커밋의 것도 아닌 값으로 남아 있었다.
    손으로 적으면 코드를 한 번 더 고칠 때 조용히 낡고, 해시로 감사하는 사람에게는
    증거 사슬 전체가 깨진 것으로 보인다. 이 검사가 그 낡음을 소리 나게 만든다.
    빨개지면 `python -X utf8 tools/record_team_d_hashes.py`를 다시 돌린다.
    """

    def test_recorded_hashes_match_the_files(self):
        spec = importlib.util.spec_from_file_location(
            "record_team_d_hashes", ROOT / "tools" / "record_team_d_hashes.py")
        recorder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recorder)
        self.assertEqual(0, recorder.main(["--check"]), "기록된 해시가 낡았다")


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

    def test_v8_does_not_fire_inside_a_scoring_table(self):
        """리뷰가 낸 v8 오탐 시나리오. 지역업체 가점과 유사실적 배점이 한 표에 있다.

        dev 음성 194건에는 창 안에 두 요건이 들어오는 공고가 없어 이 경로가 한 번도
        실행되지 않았다. dev FP=0이 이 자리를 지켜 주지 않는다.
        """
        one_line = ("□ 제안서 평가 배점표 ○ 유사용역 수행실적(10점): 최근 3년간 3억원 이상 실적 만점 "
                    "○ 지역업체 참여도(5점): 본점 소재지가 관내에 있는 업체 가점 "
                    "※ 위 항목은 평가 배점이며 입찰참가자격을 제한하지 않는다")
        many_lines = ("제안서 평가 배점표\n유사용역 수행실적(10점)\n최근 3년간 3억원 이상 실적 만점\n"
                      "지역업체 참여도(5점): 본점 소재지가 관내에 있는 업체 가점")
        for text in (one_line, many_lines):
            with self.subTest(text[:20]):
                self.assertIsNone(candidate.detect(notice(text)))

    def test_a_submission_list_after_the_clause_does_not_kill_it(self):
        """`PPS-DEV-048`이 죽었던 자리. 참가자격 뒤에 제출서류 목록이 붙는다.

        앞뒤를 같은 글자 반경으로 재면 뒤에 오는 `제출서류`가 앞의 진짜 조항을 없앤다.
        """
        text = ("참가자격\n\n다. 공고일 기준 경북에 소재한 실적이 우수한 업체.\n\n"
                "5. 심사(평가)기준 : 제안요청서 참조\n\n6. 제출서류\n\n❍ <서식1> 입찰참가신청서 1부")
        self.assertIsNotNone(candidate.detect(notice(text)))

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


UNLABELED = ROOT / "open" / "train_unlabeled.jsonl"
ALL_V6 = {"U", "L1", "L2C", "L2E"}


def load_unlabeled(ids):
    """무라벨 원본에서 레코드를 읽는다. 파일이 없으면 **건너뛰지 않고 실패한다.**

    건너뛴 초록은 검사가 없는 것과 같다(작업서). 그 파일은 gitignore 라 워크트리에
    없을 수 있고, 그때 이 검사는 빨개져야 한다.
    """
    if not UNLABELED.exists():
        raise AssertionError(
            f"{UNLABELED} 가 없다. L2 보호 사례는 실제 무라벨 레코드로만 만든다 — "
            "손으로 조립한 합성 레코드를 쓰지 않는다")
    want, found = set(ids), {}
    with UNLABELED.open(encoding="utf-8") as stream:
        for line in stream:
            rec = json.loads(line)
            if rec["id"] in want:
                found[rec["id"]] = rec
                if len(found) == len(want):
                    break
    missing = want - set(found)
    if missing:
        raise AssertionError(f"무라벨 원본에 없는 공고: {sorted(missing)}")
    return found


def with_v6(judgment, value, quote="모델이 고른 문구"):
    out = dict(judgment)
    out["v6"] = {"위반여부": value, "근거문구": quote if value == 1 else None}
    return out


def strip_lines(rec, doc_id, sentences):
    """그 문서에서 주어진 줄을 지운 사본. 변형은 조건표의 근거 문장을 지워 만든다."""
    copy_rec = json.loads(json.dumps(rec, ensure_ascii=False))
    drop = {s.strip() for s in sentences}
    for doc in copy_rec["docs"]:
        if doc.get("doc_id") != doc_id:
            continue
        doc["text"] = "\n".join(line for line in (doc.get("text") or "").split("\n")
                                if line.strip() not in drop)
    return copy_rec


class V6BasicRegionRules(unittest.TestCase):
    """D9 보호 사례 표. 규칙을 켠 상태에서 셀이 어디로 가는지를 못박는다."""

    @classmethod
    def setUpClass(cls):
        cls.recs = load_dev()

    def decide(self, rec, model_v6, rules=ALL_V6):
        return candidate.v6_decision(model_v6, rec, set(rules))

    def test_rules_are_off_unless_asked(self):
        """환경변수를 안 주면 v6 은 손대지 않는다 — 앞선 v8·v7·v4·v3 재생이 그대로 재현된다."""
        self.assertEqual(set(), candidate.enabled_v6_rules())
        rec = self.recs["PPS-DEV-102"]
        out = {"v6": {"위반여부": 1, "근거문구": "그대로"}}
        self.assertEqual(out, candidate.apply_v6(out, with_v6(empty_judgment(), 1), rec))

    def test_l1_keeps_the_region_business_phrasing_positive(self):
        """`PPS-DEV-061` — `소재지` 류 낱말 없이 `… 지역 업체` 로만 적은 정탐."""
        self.assertIsNone(self.decide(self.recs["PPS-DEV-061"], 1))

    def test_no_rule_lowers_the_basic_token_positives(self):
        """`PPS-DEV-08`·`072` — 기초 토큰이 있는 소재지 제한은 어느 규칙도 1→0 으로 못 바꾼다."""
        for rec_id in ("PPS-DEV-08", "PPS-DEV-072"):
            with self.subTest(rec_id):
                self.assertIsNone(self.decide(self.recs[rec_id], 1))

    def test_u_raises_the_two_known_false_negatives(self):
        """`PPS-DEV-070`(국가·기초 토큰)·`071`(`[수요기관(기초자치단체)]내에 소재`)."""
        for rec_id in ("PPS-DEV-070", "PPS-DEV-071"):
            with self.subTest(rec_id):
                decided = self.decide(self.recs[rec_id], 0)
                self.assertIsNotNone(decided, "U 가 올려야 한다")
                value, quote, rule = decided
                self.assertEqual((1, "U"), (value, rule))
                self.assertTrue(quote, "근거문구가 비었다")

    def test_u_evidence_survives_clean_evidence(self):
        """U 가 올린 e6 은 그 문장의 원문 부분문자열이어야 한다(D4-4)."""
        for rec_id in ("PPS-DEV-070", "PPS-DEV-071"):
            with self.subTest(rec_id):
                rec = self.recs[rec_id]
                quote = self.decide(rec, 0)[1]
                self.assertTrue(any(quote in (doc.get("text") or "") for doc in rec["docs"]),
                                "근거문구가 제공 문서의 부분문자열이 아니다")

    def test_u_does_not_raise_on_a_wide_region_short_name(self):
        """합성: `서울시 지역 업체` — 광역 축약명은 기초 신호가 아니다. 모를 때 올리지 않는다."""
        rec = self.variant_061("서울시 지역 업체")
        self.assertTrue(candidate.region_limit_sentences(rec), "지역 제한 문장 자체는 남아야 한다")
        self.assertIsNone(self.decide(rec, 0))

    def test_u_does_not_raise_on_a_wide_region_full_name(self):
        """합성: `서울특별시 지역 업체` — 광역 정식명도 마찬가지고, 모델이 1이면 L1 이 내린다."""
        rec = self.variant_061("서울특별시 지역 업체")
        self.assertIsNone(self.decide(rec, 0))
        self.assertEqual((0, None, "L1"), self.decide(rec, 1))

    def test_a_name_shared_by_a_wide_and_a_basic_region_is_not_a_basic_signal(self):
        """합성: `경기도 광주시` — 광역 축약명과 기초 지명이 겹치는 이름은 기초로 세지 않는다."""
        self.assertIsNone(self.decide(self.variant_061("경기도 광주시 지역 업체"), 0))

    def test_u_does_not_raise_on_a_common_word_ending_in_the_district_suffix(self):
        """`PPS-DEV-32`·`PPS-DEV-076` — `체결시`·`반드시` 를 기초 지명으로 읽어 올린 오탐이다.

        `script.BASIC_REGION_NAME` 이 `[가-힣]{2,4}(?:시|군|구)` 라서 보통 낱말을 문다.
        올리는 쪽은 익명화 토큰만 센다 — dev 는 전부 익명화라 기초 지명은 토큰으로 온다.
        """
        for rec_id in ("PPS-DEV-32", "PPS-DEV-076"):
            with self.subTest(rec_id):
                rec = self.recs[rec_id]
                self.assertEqual([], candidate.confirmed_basic_region_sentences(rec))
                self.assertIsNone(self.decide(rec, 0))

    def test_lowering_still_treats_an_ambiguous_name_as_basic(self):
        """내리는 쪽은 반대다 — 이름이 기초일 수 있으면 내리지 않는다."""
        rec = self.variant_061("경기도 광주시 지역 업체")
        self.assertTrue(candidate.has_basic_signal("경기도 광주시 지역 업체"))
        self.assertIsNone(self.decide(rec, 1))

    def test_u_does_not_raise_when_the_basic_token_is_a_delivery_place(self):
        """PR #114 리뷰 P1 — 한 줄에 참가 제한과 납품 장소가 같이 오는 공고.

        제한은 광역인데 기초 토큰의 역할은 납품 장소다. 줄 단위로 보면 올려 버린다.
        """
        rec = self.one_line_notice(
            "가. 입찰참가자격: 본점소재지가 경기도 [지역:r1|단위=광역|광역=경기도]에 있는 업체,"
            " 납품장소는 [지역:r2|단위=기초|광역=경기도]")
        self.assertEqual([], candidate.confirmed_basic_region_sentences(rec))
        self.assertIsNone(self.decide(rec, 0))

    # 네 라운드 연속 같은 가족에서 P1 이 났다. 원인은 "관계를 반증 없음으로 증명" 한 것이고,
    # 고친 뒤에는 **긍정 근거**를 요구한다 — 참가 업체의 소재지 주어(꼴 ①)나 융합 제한(꼴 ②).
    # 아래 표가 그 규칙의 경계를 잡는다. 앞의 여섯은 리뷰가 준 반례, 나머지는 같은 원인에서
    # 파생될 수 있는 것을 직접 만든 것이다.
    BASIC = "[지역:r2|단위=기초|광역=경기도]"
    WIDE = "[지역:r1|단위=광역|광역=경기도]"
    ROLE_CASES = [
        ("쉼표로 이은 납품장소", f"본점소재지가 경기도 {WIDE}에 있는 업체, 납품장소는 {BASIC}"),
        ("접속어미로 이은 납품장소", f"본점소재지가 경기도 {WIDE}에 있는 업체이며 납품장소는 {BASIC}"),
        ("구분자 없는 납품장소", f"본점소재지가 경기도 {WIDE}에 있는 업체 납품장소는 {BASIC}"),
        ("장소가 먼저 오는 역순", f"납품장소는 {BASIC} 본점소재지는 경기도 {WIDE}에 있는 업체"),
        ("현장 위치가 먼저", f"현장 위치: {BASIC} 주된 영업소가 경기도 {WIDE}에 있는 업체"),
        ("장소를 꾸미는 소재지", f"납품장소의 소재지가 {BASIC}이며 본점소재지는 경기도 {WIDE}에 있는 업체"),
        ("장소 소재지 단독", f"납품장소 소재지가 {BASIC}인 업체"),
        ("과업 수행 장소의 소재지", f"과업 수행 장소의 소재지가 {BASIC}이고 본점은 경기도 {WIDE}"),
        ("세미콜론으로 갈린 공사 위치", f"공사 위치의 소재지는 {BASIC}; 본점소재지는 {WIDE}"),
        ("괄호가 낀 이행 장소", f"이행 장소(납품)는 {BASIC}, 주된 영업소는 {WIDE}"),
        ("개찰 장소", f"개찰 장소는 {BASIC} 이며 본점소재지가 {WIDE}에 있는 업체"),
        ("괄호 안의 납품장소", f"본점소재지가 {WIDE}에 있는 업체(납품장소 {BASIC})"),
        ("배송지", f"배송지는 {BASIC} 본점소재지는 {WIDE}"),
        ("장소를 꾸미고 제한이 뒤에", f"납품장소의 소재지가 {BASIC}인 곳에 본점소재지를 둔 업체"),
    ]
    LIMIT_CASES = [
        ("소재지를 ~에 둔", f"주된 영업소의 소재지를 경기도 {BASIC}에 둔 업체"),
        ("괄호 낀 본점소재지", f"법인등기부상 본점소재지(개인사업자는 사업장의 소재지)가"
                            f" {BASIC} 내에 소재하고 있는 업체"),
        ("융합 지역제한", f"지역제한(경기도 {BASIC}) 대상 용역입니다."),
        ("융합 지역 업체", f"부정당업체로 제재를 받지 않은 경기도 {BASIC} 지역 업체"),
        ("주사무소 관내", f"주사무소 소재지가 경기도 {BASIC} 관내에 소재한 업체"),
    ]

    def test_u_raises_only_on_a_participant_side_location_limit(self):
        """긍정 근거가 선 문장만 올린다 — 참가 업체의 소재지 주어이거나 융합 제한이다."""
        for name, sentence in self.LIMIT_CASES:
            with self.subTest("올린다: " + name):
                rec = self.one_line_notice("가. " + sentence)
                self.assertTrue(candidate.confirmed_basic_region_sentences(rec), name)
                self.assertIsNotNone(self.decide(rec, 0), name)

    def test_u_does_not_raise_when_the_token_belongs_to_another_role(self):
        """토큰이 장소·개찰 같은 다른 역할에 속하면 어순·구분자와 무관하게 올리지 않는다."""
        for name, sentence in self.ROLE_CASES:
            with self.subTest(name):
                rec = self.one_line_notice("가. 입찰참가자격: " + sentence)
                self.assertEqual([], candidate.confirmed_basic_region_sentences(rec), name)
                self.assertIsNone(self.decide(rec, 0), name)

    def test_u_does_not_raise_when_a_connective_joins_a_delivery_place(self):
        """PR #114 재리뷰 P1 — 쉼표가 아니라 접속 어미로 이어 붙인 납품 장소.

        쉼표 유무가 아니라 **토큰의 역할**이 제한 대상에 묶이는지를 봐야 한다.
        """
        joins = ["업체이며 납품장소는", "업체, 납품장소는", "업체 납품장소는"]
        for join in joins:
            with self.subTest(join):
                rec = self.one_line_notice(
                    "가. 입찰참가자격: 본점소재지가 경기도 [지역:r1|단위=광역|광역=경기도]에 있는 "
                    + join + " [지역:r2|단위=기초|광역=경기도]")
                self.assertEqual([], candidate.confirmed_basic_region_sentences(rec))
                self.assertIsNone(self.decide(rec, 0))

    def test_u_does_not_raise_when_the_place_label_comes_first(self):
        """PR #114 재리뷰 3라운드 P1 — 장소가 제한보다 **먼저** 나오는 역순.

        토큰은 자기 앞의 가장 가까운 역할 표시에 속한다. 그것이 납품 장소면 뒤에
        참가자격 제한이 또 나오더라도 이 토큰은 제한 대상이 아니다.
        """
        cases = [
            "납품장소는 [지역:r2|단위=기초|광역=경기도] 본점소재지는 경기도"
            " [지역:r1|단위=광역|광역=경기도]에 있는 업체",
            "현장 위치: [지역:r2|단위=기초|광역=경기도] 주된 영업소가 경기도"
            " [지역:r1|단위=광역|광역=경기도]에 있는 업체",
        ]
        for tail in cases:
            with self.subTest(tail[:20]):
                rec = self.one_line_notice("가. 입찰참가자격: " + tail)
                self.assertEqual([], candidate.confirmed_basic_region_sentences(rec))
                self.assertIsNone(self.decide(rec, 0))

    def test_u_evidence_carries_the_token_even_on_a_very_long_line(self):
        """PR #114 리뷰 P1 — 480자로 앞부분만 자르면 인용에 `단위=기초` 가 안 남는다."""
        padding = "입찰참가자격 안내입니다. " * 30
        rec = self.one_line_notice(
            "가. " + padding + "본점소재지가 경기도 [지역:r1|단위=기초|광역=경기도]에 있는 업체")
        decided = self.decide(rec, 0)
        self.assertIsNotNone(decided)
        quote = decided[1]
        self.assertLessEqual(len(quote), candidate.QUOTE_MAX)
        self.assertIn("단위=기초", quote)
        self.assertIn(quote, rec["docs"][0]["text"], "근거가 원문의 연속 구간이 아니다")

    def test_u_evidence_passes_the_submission_contract(self):
        """올린 근거는 운영 후처리가 v6 에 거는 계약을 다시 통과해야 한다."""
        for rec_id in ("PPS-DEV-070", "PPS-DEV-071"):
            with self.subTest(rec_id):
                rec = self.recs[rec_id]
                quote = self.decide(rec, 0)[1]
                passed, _why = candidate.v6_evidence_contract(quote, rec)
                self.assertTrue(passed)
        self.assertEqual(
            (False, "인용 안에 기초 토큰이 없다"),
            candidate.v6_evidence_contract("본점소재지가 경기도에 있는 업체", self.recs["PPS-DEV-070"]))
        self.assertEqual(
            (False, "근거가 비었다"),
            candidate.v6_evidence_contract("", self.recs["PPS-DEV-070"]))

    def test_clause_split_keeps_a_parenthesised_comma_together(self):
        """괄호 안의 쉼표로 절을 자르면 제한 대상과 토큰이 갈라진다."""
        line = ("법인등기부상 본점소재지(개인사업자인 경우에는 사업자등록증, 허가증 등에 기재된"
                " 사업장의 소재지)가 [수요기관(기초자치단체)]내에 소재하고")
        clauses = [text for _, text in candidate._clauses(line)]
        self.assertEqual(1, len(clauses), clauses)

    def one_line_notice(self, text):
        """`PPS-DEV-070` 의 meta 를 그대로 두고 공고문만 한 줄로 바꾼 사본."""
        rec = json.loads(json.dumps(self.recs["PPS-DEV-070"], ensure_ascii=False))
        rec["docs"] = [{"doc_id": "D0", "type": "공고문", "text": text}]
        return rec

    def test_l1_lowers_the_delivery_only_basic_token(self):
        """`PPS-DEV-102` — 기초 토큰은 납품 장소에만 있고 참가 제한은 `경기도` 뿐이다."""
        rec = self.recs["PPS-DEV-102"]
        self.assertEqual((0, None, "L1"), self.decide(rec, 1))
        self.assertEqual([], candidate.basic_region_sentences(rec))

    def test_l1_does_not_lower_when_an_attachment_was_dropped(self):
        """합성: 첨부가 잘린 `061`. 못 본 문서에 근거가 있을 수 있으므로 내리지 않는다."""
        rec = json.loads(json.dumps(self.recs["PPS-DEV-061"], ensure_ascii=False))
        rec["dropped_doc_counts"] = {"과업지시서": 1}
        self.assertIsNone(self.decide(rec, 1))

    def variant_061(self, replacement):
        """`061` 의 지역 제한 문장에서 지역 표기 하나만 바꾼 사본."""
        rec = json.loads(json.dumps(self.recs["PPS-DEV-061"], ensure_ascii=False))
        token = "경기도 [지역:r1|단위=기초|광역=경기도] 지역 업체"
        for doc in rec["docs"]:
            doc["text"] = (doc.get("text") or "").replace(token, replacement)
        return rec


class V6RaisingStaysInsideTheDefinition(unittest.TestCase):
    """무라벨에서 U 가 올렸던 셀 중 참가자격 제한이 아니었던 것. 실제 공고로만 못박는다.

    dev 는 U 대상이 두 건뿐이라 이 구멍이 안 보였다. 무라벨 2,000건에서 11건 중 4건이었다.
    """

    CASES = {
        "PPS-D-008004": "소송의 관할 법원을 정한 조항이다",
        "PPS-D-012422": "과업지시서의 지역업체 보호·지원 조항이다",
        "PPS-D-004910": "동점자 우선순위이지 참가 제한이 아니다",
        "PPS-D-011742": "제한은 광역(충청북도)이고 기초 토큰은 발주기관을 가리킬 뿐이다",
    }

    @classmethod
    def setUpClass(cls):
        cls.recs = load_unlabeled(sorted(cls.CASES))

    def test_u_does_not_raise_on_sentences_that_do_not_limit_participation(self):
        for rec_id, why in self.CASES.items():
            with self.subTest(rec_id):
                rec = self.recs[rec_id]
                self.assertEqual([], candidate.confirmed_basic_region_sentences(rec), why)
                self.assertIsNone(candidate.v6_decision(0, rec, ALL_V6), why)

    def test_the_agency_token_counts_only_when_it_is_the_target(self):
        """`[수요기관(기초자치단체)]` 는 제한의 대상일 때만 기초 신호다."""
        self.assertTrue(candidate.has_confirmed_basic_signal(
            "본점소재지가 [수요기관(기초자치단체)]내에 소재하고"))
        self.assertFalse(candidate.has_confirmed_basic_signal(
            "[수요기관(기초자치단체)]이 제시하는 시방서에 따라 납품이 가능한 업체"))


class V6SmallQuoteException(unittest.TestCase):
    """L2 보호 사례. 기준 레코드는 실제 무라벨 공고이고, 변형은 조건표의 근거 문장을 지워 만든다."""

    @classmethod
    def setUpClass(cls):
        cls.recs = load_unlabeled(["PPS-D-008513", "PPS-D-009156"])

    def test_the_reference_notice_meets_all_three_conditions(self):
        """`PPS-D-008513` — (a)(b)(c) 가 모두 참이라 두 판본 모두 내린다."""
        rec = self.recs["PPS-D-008513"]
        self.assertTrue(candidate.is_small_negotiated(rec))
        checked = candidate.evaluate_small_quote_exception(rec)
        self.assertEqual((True, True, True), (checked["a"], checked["b"], checked["c"]))
        for rule in ("L2C", "L2E"):
            with self.subTest(rule):
                self.assertEqual((0, None, rule), candidate.v6_decision(1, rec, {rule}))

    def test_jurisdiction_evidence_respects_role_and_document_boundaries(self):
        """`PPS-D-009156` — (c) 의 근거는 D0 의 위치 줄 하나다.

        같은 `r2` 가 D0 의 개찰 장소 줄(역할이 다름)과 D1 의 처리장 줄(문서가 다름)에도 있다.
        """
        checked = candidate.evaluate_small_quote_exception(self.recs["PPS-D-009156"])
        self.assertTrue(checked["c"])
        self.assertEqual(["D0"], sorted({e["doc_id"] for e in checked["c_evidence"]}))
        for evidence in checked["c_evidence"]:
            self.assertNotIn("개찰", evidence["sentence"])
            self.assertNotIn("처리장", evidence["sentence"])
        self.assertEqual(1, len(checked["c_evidence"]))

    def test_jurisdiction_evidence_is_never_the_restriction_sentence_itself(self):
        """`PPS-D-013602` — `입찰 및 계약방식 지역제한([지역:r1…])` 이 제 자신을 관할 근거로 냈다."""
        rec = load_unlabeled(["PPS-D-013602"])["PPS-D-013602"]
        checked = candidate.evaluate_small_quote_exception(rec)
        limits = {x["sentence"] for x in checked["limit_sentences"]}
        for evidence in checked["c_evidence"]:
            self.assertNotIn(evidence["sentence"], limits)

    def test_a_website_menu_path_is_not_a_place(self):
        """`PPS-D-017898` — `- 위치 : 홈페이지 / 군민참여 / …` 는 납품·현장 장소가 아니다."""
        rec = load_unlabeled(["PPS-D-017898"])["PPS-D-017898"]
        checked = candidate.evaluate_small_quote_exception(rec)
        for evidence in checked["c_evidence"]:
            self.assertNotIn("홈페이지", evidence["sentence"])

    def test_electronic_quote_needs_the_quote_itself_to_be_submitted(self):
        """PR #114 리뷰 P1 — 시스템·견적서·제출이 한 창에 있어도 내는 것이 협정서면 (a) 가 아니다."""
        cases = [
            ("견적서는 나라장터에서 열람하고 공동수급협정서는 제출한다", False),
            # PR #114 재리뷰 P1 — 시스템은 열람에, 우편은 제출에 붙었다.
            ("견적서는 나라장터에서 열람하고 입찰서는 우편으로 제출한다", False),
            ("입찰서는 나라장터를 이용하여 우편으로 제출한다", False),
            ("공동수급협정서는 나라장터에서 열람하고 국가종합전자조달시스템을 이용하여"
             " 제출하여야 한다", False),
            ("견적서는 우편으로 내고 국가종합전자조달시스템을 이용하여 제출하여야 한다", False),
            # PR #114 재리뷰 3라운드 P1 — 제출 방식이 문서명 앞에 오는 어순.
            ("나라장터에서 열람 후 우편으로 입찰서를 제출한다", False),
            ("나라장터를 이용하여 방문으로 견적서를 제출한다", False),
            # 4라운드 P1 과 같은 원인에서 파생될 꼴 — 시스템은 열람·조회에 쓰였다.
            ("나라장터에서 공고문 열람 후 입찰서는 현장 접수처에 제출한다", False),
            ("입찰서는 나라장터에서 조회하고 견적서는 담당부서에 직접 제출한다", False),
            ("나라장터 공고를 확인한 뒤 견적서는 방문 접수한다", False),
            # 반대로, 시스템이 제출의 수단으로 표시되면 인정한다.
            ("견적서는 나라장터를 통하여 제출하여야 합니다.", True),
            ("입찰서는 지정정보처리장치에 제출한다", True),
            ("라. 공동수급협정서는 반드시 조달청 전자입찰시스템을 이용하여"
             " 국가종합전자조달시스템 전자 입찰 특별유의서에 따라 제출하여야 합니다.", False),
            ("사. 견적서 제출 여부는 나라장터 시스템의 전자문서함에서 확인하여야 합니다.", False),
            ("가. 국가종합전자조달시스템을 이용하여 2인 이상으로부터 견적서를 제출받는"
             " 수의계약 및 전자계약 대상입니다.", True),
            ("다. 반드시 조달청 국가종합전자조달시스템을 이용하여 제출하여야 하며,"
             " 입찰서 제출 확인은 조달청 국가종합전자조달시스템의 웹 송신함에서 확인하시기 바랍니다.", True),
        ]
        for line, expected in cases:
            with self.subTest(line[:30]):
                self.assertEqual(expected, candidate._says_electronic_quote(line))

    def test_removing_the_electronic_quote_sentences_flips_only_a(self):
        """변형: (a)만 거짓. 두 판본 모두 내리지 않는다."""
        rec = self.recs["PPS-D-008513"]
        base = candidate.evaluate_small_quote_exception(rec)
        changed = strip_lines(rec, "D0", [e["sentence"] for e in base["a_evidence"]])
        checked = candidate.evaluate_small_quote_exception(changed)
        self.assertEqual((False, base["b"], base["c"]),
                         (checked["a"], checked["b"], checked["c"]), "한 조건만 뒤집혀야 한다")
        self.assertIsNone(candidate.v6_decision(1, changed, {"L2C", "L2E"}))

    def test_raising_the_price_above_the_table_flips_only_b(self):
        """변형: (b)만 거짓. 두 판본 모두 내리지 않고, 기초 제한 문장이 남아 L1 도 내리지 않는다."""
        rec = self.recs["PPS-D-008513"]
        base = candidate.evaluate_small_quote_exception(rec)
        changed = json.loads(json.dumps(rec, ensure_ascii=False))
        changed["meta"]["입찰추정가격"] = 110_000_000
        checked = candidate.evaluate_small_quote_exception(changed)
        self.assertEqual((base["a"], False, base["c"]),
                         (checked["a"], checked["b"], checked["c"]), "한 조건만 뒤집혀야 한다")
        self.assertIsNone(candidate.v6_decision(1, changed, ALL_V6))

    def test_removing_the_site_sentence_flips_only_c(self):
        """변형: (c)만 거짓. L2-보수는 내리지 않고 L2-추정은 내린다."""
        rec = self.recs["PPS-D-008513"]
        base = candidate.evaluate_small_quote_exception(rec)
        changed = strip_lines(rec, "D0", [e["sentence"] for e in base["c_evidence"]])
        checked = candidate.evaluate_small_quote_exception(changed)
        self.assertEqual((base["a"], base["b"], False),
                         (checked["a"], checked["b"], checked["c"]), "한 조건만 뒤집혀야 한다")
        self.assertIsNone(candidate.v6_decision(1, changed, {"L2C"}))
        self.assertEqual((0, None, "L2E"), candidate.v6_decision(1, changed, {"L2E"}))


if __name__ == "__main__":
    unittest.main()
