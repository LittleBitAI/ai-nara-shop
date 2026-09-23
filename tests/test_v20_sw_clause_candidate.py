"""v20 SW 참여제한 부재 후보의 검사. 모델을 부르지 않는다."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("v20_sw_clause_candidate",
                                              ROOT / "experiments/v20_sw_clause_candidate.py")
candidate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = candidate
spec.loader.exec_module(candidate)


def rec(text, licenses=None):
    return {"meta": {"면허업종제한목록": licenses}, "docs": [{"type": "공고문", "text": text}]}


class SignalTest(unittest.TestCase):
    def test_not_software_is_none(self):
        self.assertIsNone(candidate.sw_participation_missing(rec("물품 구매 공고")))

    def test_meta_license_without_clause(self):
        r = rec("입찰 공고", "[소프트웨어사업자(컴퓨터관련서비스사업)(1468)]")
        self.assertIs(candidate.sw_participation_missing(r), True)

    def test_text_requirement_with_clause(self):
        r = rec("소프트웨어사업자(컴퓨터 관련 서비스사업)로 신고한 업체 "
                "※ 소프트웨어진흥법 제48조에 따른 소프트웨어사업자의 사업금액별 참여 제한")
        self.assertIs(candidate.sw_participation_missing(r), False)

    def test_other_article_48_is_not_the_clause(self):
        # 동가 입찰 조항(계약법 시행령 제48조)을 SW 참여제한으로 읽으면 안 된다.
        r = rec("「지방자치단체를 당사자로 하는 계약에 관한 법률 시행령」 제48조에 따라 낙찰자를 결정",
                "[소프트웨어사업자(컴퓨터관련서비스사업)(1468)]")
        self.assertIs(candidate.sw_participation_missing(r), True)


class DecisionTest(unittest.TestCase):
    def test_no_software_registration_removes(self):
        self.assertEqual(candidate.v20_decision(rec("물품 구매 공고")), 0)

    def test_clause_removes_even_with_1468(self):
        r = rec("「소프트웨어 진흥법」제48조에 따라 중소 소프트웨어사업자만 입찰참가 가능",
                "[소프트웨어사업자(컴퓨터관련서비스사업)(1468)]")
        self.assertEqual(candidate.v20_decision(r), 0)

    def test_clause_outside_judgment_docs_abstains(self):
        # PPS-D-001203 shape: the sentence only in 과업지시서 does not settle v20.
        r = {"meta": {"면허업종제한목록": "[소프트웨어사업자(컴퓨터관련서비스사업)(1468)]"},
             "docs": [{"type": "공고문", "text": "입찰 공고"},
                      {"type": "과업지시서", "text": "「소프트웨어 진흥법」제48조에 따른 참여 제한"}]}
        self.assertIsNone(candidate.v20_decision(r))

    def test_old_article_and_floor_notice_remove(self):
        # PPS-D-018645 shape: pre-renumbering 제24조의2 and the 하한 고시 title, split by a line break.
        r = rec("다. 소프트웨어산업진흥법 제24조의 2에 따른 대기업인 소프트웨어사업자가 참여할 수 있는 사\n\n업금액의 하한",
                "[소프트웨어사업자(컴퓨터관련서비스사업)(1468)]")
        self.assertEqual(candidate.v20_decision(r), 0)

    def test_halfwidth_bracket_citation_removes(self):
        # PPS-D-019424 shape: ｢…｣ half-width brackets around the law name.
        r = rec("｢소프트웨어 진흥법｣ 제48조제2항에 따라 대기업의 입찰 참여를 제한",
                "[소프트웨어사업자(컴퓨터관련서비스사업)(1468)]")
        self.assertEqual(candidate.v20_decision(r), 0)

    def test_bare_sme_software_name_abstains(self):
        # PPS-D-004071 shape: a 시행령 제41조 title as a qualification is not the restriction.
        r = rec("「소프트웨어 진흥법 시행령」 제41조(중소 소프트웨어사업자의 기준 등) 제1항 제1호에 해당하는 자",
                "[소프트웨어사업자(컴퓨터관련서비스사업)(1468)]")
        self.assertIsNone(candidate.v20_decision(r))

    def test_1468_in_other_wording_adds(self):
        r = rec("소프트웨어사업자(업종코드:1468)와 정보통신공사업(업종코드:0036)로 입찰참가 등록한 자")
        self.assertEqual(candidate.v20_decision(r), 1)

    def test_other_software_category_abstains(self):
        r = rec("입찰 공고", "[소프트웨어사업자(패키지소프트웨어개발.공급사업)(1426)]")
        self.assertIsNone(candidate.v20_decision(r))

    def test_uncoded_registration_abstains(self):
        r = rec("소프트웨어산업진흥법에 의한 소프트웨어사업자 등록 업체 또는 이러닝 사업자 등록 업체")
        self.assertIsNone(candidate.v20_decision(r))


class DevTest(unittest.TestCase):
    def test_dev_firing_set(self):
        # dev 200건의 발화 집합. 양성 5건 전부와 오탐 124·135.
        fired = set()
        with open(ROOT / "open/dev.jsonl", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if candidate.sw_participation_missing(r):
                    fired.add(r["id"])
        self.assertEqual(fired, {"PPS-DEV-24", "PPS-DEV-131", "PPS-DEV-132", "PPS-DEV-133",
                                 "PPS-DEV-134", "PPS-DEV-124", "PPS-DEV-135"})


if __name__ == "__main__":
    unittest.main()
