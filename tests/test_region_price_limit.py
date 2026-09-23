"""지방계약 지역제한 상한(v5·v6·v7의 `고시금액`)의 검사.

근거는 2026-09-23 데이콘 공지다 — 시·도(세종 제외)가 발주하는 물품·일반용역은 3억 5천만원,
세종·시·군·구·교육청(학교)·지방공기업은 5억원. v2·v14~v16 의 2억 3천만원은 그대로다.
"""

from __future__ import annotations

import unittest

import script

QUALIFICATION = "입찰참가자격 본점 소재지를 경기도 또는 서울특별시의 관할구역 안에 둔 업체"


def notice(agency, owner="지방정부", price=400_000_000, extra=""):
    text = f"[수요기관({agency})] 공고 [공고번호]\n{extra}\n{QUALIFICATION}"
    return {"id": "T", "docs": [{"doc_id": "d1", "type": "공고문", "text": text}],
            "meta": {"적용계약법": "지방계약법", "업무구분": "일반용역", "소관구분": owner,
                     "입찰추정가격": price}}


class LocalGoodsServiceLimit(unittest.TestCase):

    def test_province_uses_the_notice_amount(self):
        for agency in ("지방정부", "광역자치단체"):
            with self.subTest(agency):
                self.assertEqual(350_000_000, script.region_price_limit(notice(agency)))

    def test_sejong_and_lower_tiers_use_five_hundred_million(self):
        cases = (notice("지방정부", extra="[지역:r1|단위=기초|광역=세종특별자치시]"),
                 notice("기초자치단체"),
                 notice("중학교", owner="교육기관"),
                 notice("교육청", owner="교육기관"),
                 notice("공기업", owner="지방공기업"),
                 notice("보건기관"))       # 시·도인지 모르는 기관은 조문의 5억 쪽이다
        for rec in cases:
            with self.subTest(rec["docs"][0]["text"][:30]):
                self.assertEqual(500_000_000, script.region_price_limit(rec))

    def test_the_ordering_agency_is_the_first_token(self):
        """시·군 공고 본문이 도를 언급해도 발주기관은 머리의 기관이다."""
        rec = notice("기초자치단체", extra="[수요기관(지방정부)] 보조사업")
        self.assertEqual(500_000_000, script.region_price_limit(rec))

    def test_v7_is_suppressed_from_the_province_limit(self):
        rec = notice("지방정부", price=350_000_000)
        self.assertIsNone(script.detect_region_expansion(rec))
        rec["meta"]["입찰추정가격"] = 349_999_999
        self.assertIsNotNone(script.detect_region_expansion(rec))
        # 같은 금액이라도 시·군·구 공고면 5억 미만이라 막지 않는다
        self.assertIsNotNone(script.detect_region_expansion(notice("기초자치단체",
                                                                  price=450_000_000)))


class V5Gate(unittest.TestCase):
    """v5(고시금액 이상 지역제한)는 지방계약에서 지역제한 상한 미만이면 부정된다."""

    EVIDENCE = QUALIFICATION

    def refuted(self, rec):
        return script.evidence_refutes("v5", self.EVIDENCE, rec)

    def test_local_below_the_region_limit_is_not_v5(self):
        self.assertTrue(self.refuted(notice("기초자치단체", price=400_000_000)))
        self.assertTrue(self.refuted(notice("지방정부", price=300_000_000)))

    def test_local_at_or_above_the_region_limit_stays(self):
        self.assertFalse(self.refuted(notice("기초자치단체", price=500_000_000)))
        self.assertFalse(self.refuted(notice("지방정부", price=350_000_000)))

    def test_national_keeps_the_notice_amount(self):
        rec = notice("국가기관", owner="국가기관", price=230_000_000)
        rec["meta"]["적용계약법"] = "국가계약법"
        self.assertFalse(self.refuted(rec))
        rec["meta"]["입찰추정가격"] = 229_999_999
        self.assertTrue(self.refuted(rec))

    def test_other_amount_items_keep_230_million(self):
        """v2·v14~v16 의 고시금액은 이번 공지의 보완 대상이 아니다."""
        self.assertEqual(230_000_000, script.NOTICE_AMOUNT_WON)


if __name__ == "__main__":
    unittest.main()
