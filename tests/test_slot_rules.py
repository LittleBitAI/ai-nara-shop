import importlib.util
import unittest
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


if __name__ == "__main__":
    unittest.main()
