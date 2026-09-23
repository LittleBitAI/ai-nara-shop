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

    def test_sejong_elsewhere_in_the_notice_does_not_change_the_agency(self):
        """세종은 발주기관의 지역일 때만이다. 첨부의 납품 장소는 발주기관이 아니다."""
        rec = notice("지방정부", extra="[지역:r1|단위=기초|광역=경기도] 청사")
        rec["docs"].append({"doc_id": "d2", "type": "규격서",
                            "text": "납품장소 [지역:r2|단위=읍면동|광역=세종특별자치시]"})
        self.assertEqual(350_000_000, script.region_price_limit(rec))
        # 공고문 안이라도 납품 장소의 세종은 발주기관이 아니다
        in_notice = notice("지방정부", extra="[지역:r1|단위=기초|광역=경기도] 청사\n"
                                           "납품장소 [지역:r2|단위=읍면동|광역=세종특별자치시]")
        self.assertEqual(350_000_000, script.region_price_limit(in_notice))
        linked = notice("지방정부", extra="[지역:r1|단위=광역|광역=세종특별자치시] 청사")
        linked["docs"][0]["text"] = linked["docs"][0]["text"].replace(
            "[수요기관(지방정부)]", "[수요기관(지방정부)|지역=r1]")
        self.assertEqual(500_000_000, script.region_price_limit(linked))
        only_sejong = notice("지방정부", extra="[지역:r1|단위=기초|광역=세종특별자치시] 청사")
        self.assertEqual(500_000_000, script.region_price_limit(only_sejong))

    def test_document_order_does_not_decide_the_agency(self):
        """발주기관은 공고문에서 읽는다. 배열 순서가 바뀌어도 같은 값이어야 한다."""
        rec = notice("지방정부")
        rec["docs"].insert(0, {"doc_id": "d0", "type": "규격서",
                               "text": "[수요기관(기초자치단체)] 과업지시서"})
        self.assertEqual(350_000_000, script.region_price_limit(rec))

    def test_special_services_use_their_own_limit_first(self):
        """안전점검·정밀안전진단 1억 5천만원, 건설기술·설계·감리·엔지니어링 3억 3천만원."""
        cases = (("지방정부", "용 역 명: 교량 정밀안전진단 용역", 150_000_000),
                 ("기초자치단체", "용 역 명: 정밀안전점검 용역", 150_000_000),
                 ("지방정부", "용 역 명: 도로 실시설계 용역", 330_000_000),
                 ("기초자치단체", "용 역 명: 하수관로 건설사업관리(감리) 감리용역", 330_000_000))
        for agency, head, limit in cases:
            with self.subTest(head):
                rec = notice(agency, extra=head)
                self.assertEqual(limit, script.region_price_limit(rec))
                rec["meta"]["입찰추정가격"] = limit
                self.assertFalse(script.evidence_refutes("v5", QUALIFICATION, rec))

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
