"""v3·v17 삭제형 후보의 검사.

모델을 부르지 않는다. 두 규칙이 **1을 0으로만** 내리고, 자기 항목 밖을 건드리지 않고,
보관 회차에서 정확히 판정 문서가 오탐이라 한 여덟 셀만 닫는지를 고정한다.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import replay_run  # noqa: E402

# 후보가 운영 코드를 `submission` 이름으로 집으므로 그 이름으로 먼저 싣는다.
script = replay_run.load_module(ROOT / "script.py", "submission")


def load_candidate():
    spec = importlib.util.spec_from_file_location(
        "quoted_deletion_candidate", ROOT / "experiments/quoted_deletion_candidate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


candidate = load_candidate()
# 전체 실행에서는 다른 검사 파일이 수집 시점에 `submission` 을 제 모듈로 갈아 꽂는다.
# 카탈로그를 안 채운 그 모듈을 후보가 집으면 재생이 어긋나므로, 여기서 실은 것에 묶는다.
candidate.baseline = lambda: script

CASE = ROOT / "reports/runs/colab-1789902969401579900/dev-debug"

# 판정 문서(artifacts/review/quoted-fp-result.md)가 `오탐` 이라 한 셀. 이 회차 재생에서
# 바뀌는 셀은 정확히 이 여덟이어야 한다. 하나라도 늘거나 줄면 규칙이 문서와 갈라진 것이다.
EXPECTED_CHANGED = {
    ("PPS-DEV-03", "v3"), ("PPS-DEV-25", "v3"), ("PPS-DEV-112", "v3"), ("PPS-DEV-170", "v3"),
    ("PPS-DEV-038", "v17"), ("PPS-DEV-102", "v17"), ("PPS-DEV-120", "v17"), ("PPS-DEV-172", "v17"),
}


def notice(text, estimated=89_090_909, budget=98_000_000):
    return {"id": "T", "meta": {"입찰추정가격": estimated, "배정예산금액": budget},
            "docs": [{"text": text}]}


class V3Amount(unittest.TestCase):
    """인용이 적은 요구실적 금액이 사업예산 1배 미만이면 1배수 제한이 아니다."""

    def test_amount_below_both_bases_is_deleted(self):
        quote = "공고일 기준 5년 이내 공공디자인 용역 실적이 3천만원 이상인 업체"
        self.assertEqual(candidate.v3_deletion(quote, notice(quote)), "below_budget")

    def test_amount_above_basis_is_kept(self):
        quote = "최근 5년 간 단일 건으로 455,000,000원 이상의 수행실적"
        self.assertIsNone(candidate.v3_deletion(quote, notice(quote, 318_181_818, 350_000_000)))

    def test_amount_between_estimate_and_budget_is_kept(self):
        """추정가격보다 크고 배정예산보다 작으면 기준 선택에 따라 갈린다. 내리지 않는다."""
        quote = "단일 건 95,000,000원 이상 실적"
        self.assertIsNone(candidate.v3_deletion(quote, notice(quote, 90_000_000, 100_000_000)))

    def test_largest_amount_in_quote_decides(self):
        """인용에 금액이 여럿이면 가장 큰 것으로 본다. 하나라도 예산 이상이면 내리지 않는다."""
        quote = "3천만원 이상 실적 또는 단일 건 1억원 이상 실적"
        self.assertIsNone(candidate.v3_deletion(quote, notice(quote)))

    def test_percent_of_hundred_or_more_blocks_amount_rule(self):
        quote = "3천만원(기초금액의 130% 이상) 실적"
        self.assertIsNone(candidate.v3_deletion(quote, notice(quote)))

    def test_amount_outside_the_performance_clause_is_ignored(self):
        """리뷰 라운드 3: 자본금처럼 실적이 아닌 금액을 요구실적액으로 읽지 않는다."""
        for quote in ("자본금 3천만원 이상 및 최근 5년간 사업예산의 1배 이상 수행실적을 보유한 업체",
                      "자본금 3천만원 이상, 동종 실적 1건 이상 보유 업체"):
            with self.subTest(quote=quote):
                self.assertIsNone(candidate.v3_deletion(quote, notice(quote)))

    def test_multiple_of_one_or_more_blocks_amount_rule(self):
        quote = "수행실적 3천만원 이상(사업예산의 1.5배 이상)"
        self.assertIsNone(candidate.v3_deletion(quote, notice(quote)))

    def test_performance_amount_beside_other_amount_still_decides(self):
        quote = "자본금 5억원 이상 및 최근 3년 이내 동종 용역 실적 3천만원 이상"
        self.assertEqual(candidate.v3_deletion(quote, notice(quote)), "below_budget")

    def test_no_amount_and_no_percent_is_kept(self):
        quote = "동종 용역 수행실적이 있는 업체"
        self.assertIsNone(candidate.v3_deletion(quote, notice(quote)))

    def test_missing_basis_is_kept(self):
        quote = "실적이 3천만원 이상인 업체"
        rec = {"id": "T", "meta": {}, "docs": [{"text": quote}]}
        self.assertIsNone(candidate.v3_deletion(quote, rec))


class V3ScoringBand(unittest.TestCase):
    """배점표의 최상위 구간은 참가자격 최저실적이 아니다."""

    TABLE = ("평가항목 | 평가기준 | 배점\n"
             "유사사업 수행실적 | 예산금액의 100% 이상 | 6 |\n"
             "예산금액의 80% 이상 | 4\n예산금액의 80% 미만 | 2\n")

    def test_top_band_of_scoring_table_is_deleted(self):
        self.assertEqual(candidate.v3_deletion("예산금액의 100% 이상", notice(self.TABLE)),
                         "scoring_band")

    def test_eligibility_percent_without_lower_band_is_kept(self):
        text = "참가자격: 기초금액의 100% 이상 실적이 있는 업체\n기타 사항은 공고문에 따른다."
        self.assertIsNone(candidate.v3_deletion("기초금액의 100% 이상 실적", notice(text)))

    def test_scoring_cue_without_lower_band_is_kept(self):
        text = "제안서 평가 후 적격자를 정한다.\n참가자격: 기초금액의 100% 이상 실적이 있는 업체\n"
        self.assertIsNone(candidate.v3_deletion("기초금액의 100% 이상 실적", notice(text)))

    def test_lower_band_without_scoring_cue_is_kept(self):
        text = "참가자격\n가. 입찰 금액의 100% 이상\n나. 입찰 금액의 60% 이상 100% 미만\n"
        self.assertIsNone(candidate.v3_deletion("가. 입찰 금액의 100% 이상", notice(text)))

    def test_qualification_between_scoring_text_and_lower_band_is_kept(self):
        """리뷰 라운드 1: 평가 절 뒤에 참가자격 절이 오면 그 사이의 경계를 넘지 않는다."""
        text = ("제안서 평가 기준 및 배점: 가격평가 20점.\n"
                "입찰참가자격: 사업예산의 100% 이상 실적이 있는 업체로 제한한다.\n"
                "평가 가점: 사업예산의 80% 이상은 4점")
        for quote in ("입찰참가자격: 사업예산의 100% 이상 실적이 있는 업체로 제한한다.",
                      "사업예산의 100% 이상 실적이 있는 업체"):
            with self.subTest(quote=quote):
                self.assertIsNone(candidate.v3_deletion(quote, notice(text)))

    def test_other_qualification_wording_between_is_kept(self):
        """리뷰 라운드 2: 자격 표지 목록에 없는 표기라도 표의 다음 행이 아니면 구간으로 보지 않는다."""
        text = ("제안서 평가 기준 및 배점: 가격평가 20점.\n"
                "입찰에 참가할 수 있는 자: 사업예산의 100% 이상 실적이 있는 업체.\n"
                "평가 가점: 사업예산의 80% 이상은 4점")
        for quote in ("사업예산의 100% 이상 실적이 있는 업체", "사업예산의 100% 이상"):
            with self.subTest(quote=quote):
                self.assertIsNone(candidate.v3_deletion(quote, notice(text)))

    def test_quote_also_used_as_qualification_is_kept(self):
        """리뷰 라운드 2: 같은 문구가 배점표와 참가자격에 모두 나오면 어느 쪽 근거인지 모른다."""
        text = ("평가항목 | 배점\n수행실적 | 예산의 100% 이상 | 6점\n예산의 80% 이상 | 4점\n"
                "참가자격: 예산의 100% 이상 수행실적을 보유한 업체")
        self.assertIsNone(candidate.v3_deletion("예산의 100% 이상", notice(text)))

    def test_repeated_same_band_is_not_a_table(self):
        text = "평가 배점\n참가자격\n가. 사업예산의 100% 이상\n나. 사업예산의 100% 이상 실적 증명서를 낸다"
        self.assertIsNone(candidate.v3_deletion("가. 사업예산의 100% 이상", notice(text)))

    def test_lower_band_of_different_base_is_kept(self):
        text = "평가 배점\n참가자격 | 사업예산의 100% 이상 | \n신용평가 | 등급 80% 이상"
        self.assertIsNone(candidate.v3_deletion("사업예산의 100% 이상", notice(text)))

    def test_quote_not_in_documents_is_kept(self):
        self.assertIsNone(candidate.v3_deletion("예산금액의 100% 이상", notice("무관한 본문 배점")))


class V17MidSizeEntity(unittest.TestCase):
    """v17 은 중기업까지 허용한 제한이다. 인용이 그 자격을 세우지 못하면 내린다."""

    def test_small_business_only_is_deleted(self):
        for quote in ("거. 소기업 또는 소상공인확인서 1부",
                      "소기업(소상공인) 확인서를(응찰(개찰)일 까지 발급된 것) 소지한 업체",
                      "「중소기업기본법」 제2조제2항에 따른 소기업 또는 「소상공인기본법」 제2조에 따른 "
                      "소상공인으로서 「중소기업 범위 및 확인에 관한 규정」에 따라 발급된 "
                      "소기업·소상공인 확인서를 소지한 자",
                      "중소기업기본법 제2조에 따른 소기업자",
                      "「중소기업진흥에 관한 법률」에 따른 소기업"):
            with self.subTest(quote=quote):
                self.assertEqual(candidate.v17_deletion(quote), "no_mid_size_entity")

    def test_other_qualification_is_deleted(self):
        self.assertEqual(candidate.v17_deletion("「여성기업지원에 관한 법률」 제2조 제1호에 따른 여성기업"),
                         "no_mid_size_entity")

    def test_mid_size_entity_is_kept(self):
        for quote in ("「중소기업기본법」제2조에 따른 중소기업 또는 소상공인으로서 확인서를 소지한 자",
                      "「중소기업제품 구매촉진 및 판로지원에 관한 법률」 제8조의 요건을 갖춘 중소기업자",
                      "중소기업기본법 제2조 제2항에 따른 중·소기업 또는 소상공인",
                      "｢중소기업기본법｣ 제2조에 따른 중・소기업자",
                      "중,소기업제한", "중기업 및 소기업",
                      # 리뷰 라운드 1: 인용 부호로 묶인 자격 주체는 법령 이름이 아니다
                      "참가자격은 「중소기업」 또는 「소상공인」으로 제한한다",
                      # 같은 결함의 괄호 없는 쪽: 법령 이름의 앞머리만 보고 자격 주체를 지우지 않는다
                      "중소기업 범위에 해당하는 업체", "중소기업제품을 생산하는 업체"):
            with self.subTest(quote=quote):
                self.assertIsNone(candidate.v17_deletion(quote))

    def test_empty_quote_is_left_to_the_evidence_contract(self):
        self.assertIsNone(candidate.v17_deletion(""))


class Postprocess(unittest.TestCase):

    def test_never_raises_and_touches_only_its_items(self):
        judgment = {v: {"위반여부": 0, "근거문구": None} for v in script.ITEMS}
        rec = notice("실적이 3천만원 이상인 업체")
        out = candidate.postprocess(judgment, rec)
        self.assertEqual(out, script.postprocess(judgment, rec))


class ReplayStoredRun(unittest.TestCase):
    """보관 회차의 원응답으로 전 경로를 태워 바뀌는 셀을 고정한다."""

    @classmethod
    def setUpClass(cls):
        if not (CASE / "diagnostics.jsonl").is_file():
            raise unittest.SkipTest(f"{CASE} 가 없다")
        kwargs = dict(input_path=ROOT / "open/dev.jsonl", data_dir=ROOT / "open/data")
        cls.base = replay_run.replay(script, CASE, **kwargs)["rows"]
        cls.cand = replay_run.replay(script, CASE, postprocess=candidate.postprocess, **kwargs)["rows"]

    def test_changes_exactly_the_adjudicated_false_positives(self):
        changed = set()
        for before, after in zip(self.base, self.cand):
            self.assertEqual(before["id"], after["id"])
            for item in script.ITEMS:
                if before[item] != after[item]:
                    self.assertEqual((before[item], after[item]), (1, 0), (before["id"], item))
                    changed.add((before["id"], item))
        self.assertEqual(changed, EXPECTED_CHANGED)


if __name__ == "__main__":
    unittest.main()
