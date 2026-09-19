"""경쟁제품 규칙(v11·v12)의 검사.

모델을 부르지 않는다. 제공 고시 카탈로그와 dev 원문으로만 잰다.

이 규칙이 하는 말은 하나다 — **직생을 요구한 공고에서, 그 요구가 지목한 품명이
중기간 경쟁제품인가.** 그 판정에 고시 `특이사항`의 금액 상한이 들어간다는 것이
기존 코드와 다른 점이고, 아래 `test_amount_cap_flips_the_gate` 가 그 자리를 지킨다.
"""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

import script

REPO = Path(__file__).resolve().parents[1]
DEV = REPO / "open/dev.jsonl"
LABELS = REPO / "open/dev_labels.csv"
CATALOGUE = REPO / "open/data/법령패키지/중기부고시/중기부고시_경쟁제품_세부품명.csv"


def load_products():
    with CATALOGUE.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def load_dev():
    with DEV.open(encoding="utf-8") as stream:
        return {r["id"]: r for r in (json.loads(line) for line in stream if line.strip())}


class CompetitiveProductTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recs = load_dev()
        cls.truth = {r["id"]: r for r in csv.DictReader(LABELS.open(encoding="utf-8"))}
        script._PRODUCTS[:] = load_products()

    def judge(self, notice_id):
        blank = {v: {"위반여부": 0, "근거문구": None} for v in script.ITEMS}
        return script.apply_product_rules(blank, self.recs[notice_id])

    # ----- 고시 특이사항의 금액 상한이 게이트를 뒤집는다 -----
    def test_amount_cap_flips_the_gate(self):
        """축제기획및대행서비스(9015189001)는 "추정가격 3억원 미만에 한함"이다.

        `PPS-DEV-054`는 그 품명으로 직생을 요구했고 추정가격이 3.27억이다.
        상한을 넘었으므로 경쟁제품이 아니고, 따라서 직생 요구가 v12 위반이다.
        상한을 안 보면 이 공고는 경쟁제품으로 읽혀 v12를 놓친다.
        """
        rec = self.recs["PPS-DEV-054"]
        _, codes = script.direct_production_demand(rec)
        self.assertIn("9015189001", codes)
        self.assertGreaterEqual(script.estimated_price(rec), 300_000_000)
        self.assertIs(script.competitive_product(rec, codes), False)
        self.assertEqual(self.judge("PPS-DEV-054")["v12"]["위반여부"], 1)

        row = next(p for p in script._PRODUCTS if p["세부품명번호"] == "9015189001")
        self.assertEqual(script.product_cap_won(row), 300_000_000)

    # ----- 사후 제재 문구는 참가자격 요구가 아니다 -----
    def test_sanction_clause_is_not_a_demand(self):
        """`PPS-DEV-064`의 직접생산 언급은 "확인기준을 위반한 사실을 확인한 경우"의
        계약 후 제재 안내뿐이다. 이것을 요구로 읽으면 규칙이 엉뚱한 공고에서 발화한다."""
        quote, _ = script.direct_production_demand(self.recs["PPS-DEV-064"])
        self.assertIsNone(quote)
        self.assertEqual(self.judge("PPS-DEV-064"), {v: {"위반여부": 0, "근거문구": None}
                                                     for v in script.ITEMS})

    # ----- 부재탐지 v11의 근거는 항상 빈칸이다 (data.md D4-5) -----
    def test_v11_evidence_is_always_blank(self):
        fired = [i for i in self.recs if self.judge(i)["v11"]["위반여부"] == 1]
        self.assertTrue(fired, "v11이 dev에서 한 번도 발화하지 않는다")
        for notice_id in fired:
            self.assertIsNone(self.judge(notice_id)["v11"]["근거문구"])

    # ----- v12의 근거는 원문의 연속된 부분문자열이다 (D4-4) -----
    def test_v12_evidence_is_verbatim(self):
        fired = [i for i in self.recs if self.judge(i)["v12"]["위반여부"] == 1]
        self.assertTrue(fired, "v12가 dev에서 한 번도 발화하지 않는다")
        for notice_id in fired:
            quote = self.judge(notice_id)["v12"]["근거문구"]
            self.assertLessEqual(len(quote), script.EVIDENCE_MAX)
            self.assertTrue(any(quote in doc["text"] for doc in self.recs[notice_id]["docs"]),
                            f"{notice_id}: 근거가 원문의 부분문자열이 아니다")

    # ----- 카탈로그가 없으면 규칙은 아무 말도 하지 않는다 -----
    def test_rule_is_silent_without_catalogue(self):
        saved = list(script._PRODUCTS)
        script._PRODUCTS.clear()
        try:
            self.assertIs(script.competitive_product(self.recs["PPS-DEV-054"], {"9015189001"}), None)
        finally:
            script._PRODUCTS[:] = saved

    # ----- 규칙이 정답 양성을 깎지 않는다 -----
    def test_rule_only_raises_and_finds_true_positives(self):
        """올리기만 하는 규칙이므로 FN은 늘 수 없고, dev에서 두 항목 모두 TP가 선다."""
        gained = {"v11": 0, "v12": 0}
        false_positive = {"v11": 0, "v12": 0}
        for notice_id in self.recs:
            out = self.judge(notice_id)
            for item in gained:
                if out[item]["위반여부"] == 1:
                    key = gained if self.truth[notice_id][item] == "1" else false_positive
                    key[item] += 1
        self.assertGreaterEqual(gained["v11"], 2)
        self.assertGreaterEqual(gained["v12"], 2)
        # 오탐이 늘면 알아차린다. 실측은 v11 2건·v12 0건이고, 넘으면 게이트가 헐거워진 것이다.
        self.assertLessEqual(false_positive["v11"], 2)
        self.assertLessEqual(false_positive["v12"], 0)


if __name__ == "__main__":
    unittest.main()
