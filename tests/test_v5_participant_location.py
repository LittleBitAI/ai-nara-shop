"""v5 고시금액 이상 참가업체 소재지 제한 올림의 경계 검사."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("v5_participant_location", ROOT / "script.py")
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)


def notice(text, price):
    return {
        "id": "fixture",
        "docs": [{"doc_id": "notice", "type": "공고문", "text": text}],
        "meta": {
            "적용계약법": "국가계약법",
            "업무구분": "일반용역",
            "입찰추정가격": price,
        },
    }


def zero_judgment():
    return {item: {"위반여부": 0, "근거문구": None} for item in script.ITEMS}


class V5ParticipantLocationTests(unittest.TestCase):
    def test_high_band_qualification_participant_location_raises_with_evidence(self):
        line = "주된 영업소의 소재지가 경기도인 업체"
        rec = notice("입찰참가자격\n" + line, 230_000_000)

        self.assertEqual(script.v5_should_raise(rec), line)
        result = script.postprocess(zero_judgment(), rec)
        self.assertEqual(result["v5"], {"위반여부": 1, "근거문구": line})

    def test_below_region_price_limit_does_not_raise(self):
        rec = notice("입찰참가자격\n주된 영업소의 소재지가 경기도인 업체", 229_999_999)

        self.assertIsNone(script.v5_should_raise(rec))
        self.assertEqual(script.postprocess(zero_judgment(), rec)["v5"]["위반여부"], 0)

    def test_delivery_or_work_area_is_not_participant_location_restriction(self):
        for line in (
            "납품장소는 경기도에 있는 업체로 한다",
            "용역 수행지역은 경기도에 있는 업체의 사업장이다",
        ):
            with self.subTest(line=line):
                rec = notice("입찰참가자격\n" + line, 230_000_000)
                self.assertIsNone(script.v5_should_raise(rec))
                self.assertEqual(script.postprocess(zero_judgment(), rec)["v5"]["위반여부"], 0)


if __name__ == "__main__":
    unittest.main()
