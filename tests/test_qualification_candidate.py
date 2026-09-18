"""v8 중복제한 후보 검사. 모델을 부르지 않는다. live 성능 검사가 아니다."""

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

# 실제 dev 정답의 v8 양성 전수. 여기서 하나라도 빠지면 후보가 후퇴한 것이다.
POSITIVES = ["PPS-DEV-05", "PPS-DEV-11", "PPS-DEV-042",
             "PPS-DEV-048", "PPS-DEV-054", "PPS-DEV-071"]


def load_dev():
    return {json.loads(line)["id"]: json.loads(line)
            for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()}


def load_truth():
    with LABELS.open(encoding="utf-8", newline="") as stream:
        return {row["id"]: row["v8"] == "1" for row in csv.DictReader(stream)}


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

    def test_requirements_in_different_documents_do_not_fire(self):
        rec = {"id": "sample", "meta": {},
               "docs": [{"doc_id": "a", "type": "공고문",
                         "text": "참가자격 주된 영업소가 서울특별시 관내에 있는 업체"},
                        {"doc_id": "b", "type": "과업지시서",
                         "text": "최근 3년 이내 1억원 이상의 실적을 보유한 업체"}]}
        self.assertIsNone(candidate.detect(rec))


class ApplyContract(unittest.TestCase):
    def test_only_v8_changes(self):
        rec = load_dev()["PPS-DEV-11"]
        before = empty_judgment()
        after = candidate.apply(before, rec)
        self.assertEqual(1, after["v8"]["위반여부"])
        for item in after:
            if item != "v8":
                self.assertEqual(before[item], after[item])

    def test_model_positive_is_kept_untouched(self):
        rec = load_dev()["PPS-DEV-11"]
        before = empty_judgment()
        before["v8"] = {"위반여부": 1, "근거문구": "모델이 고른 문구"}
        self.assertEqual(before["v8"], candidate.apply(before, rec)["v8"])

    def test_rule_never_downgrades_a_negative_to_a_different_value(self):
        rec = notice("이 공고에는 아무 제한도 없다")
        after = candidate.apply(empty_judgment(), rec)
        self.assertEqual(0, after["v8"]["위반여부"])

    def test_input_is_not_mutated(self):
        rec = load_dev()["PPS-DEV-11"]
        before = empty_judgment()
        snapshot = json.dumps(before, ensure_ascii=False, sort_keys=True)
        candidate.apply(before, rec)
        self.assertEqual(snapshot, json.dumps(before, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
