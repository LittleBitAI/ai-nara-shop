"""C3 후보의 금액 게이트 검사.

모델을 부르지 않는다. 경계값과, 보관된 진단 회차의 실제 판정으로 잰다.
"""

from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

from experiments import sme_candidate as candidate

REPO = Path(__file__).resolve().parents[1]
DIAGNOSE = REPO / "reports/runs/colab-1789658250172468461/diagnose/items.jsonl"
DEV = REPO / "open/dev.jsonl"

# 회차 `colab-1789658250172468461`(별도 `판정` 칸을 둔 **느슨한** 질의)에 조문 확정
# 고시금액 2.3억을 씌운 값이다. **다른 회차에 그대로 기대하면 안 된다** — 판정을 묻는
# 방식만 바꾼 `colab-1789695980726180378` 에서는 같은 게이트가 v16 1/17/5, v18 2/29/5 다.
# 회차를 가로질러 서는 것은 아래 test_gate_removes_no_true_positive 의 불변식뿐이다.
EXPECTED = {
    "v16": {"tp": 6, "fp": 39, "fn": 0},
    "v18": {"tp": 4, "fp": 51, "fn": 3},
}


def load_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def rec_with(price):
    return {"id": "X", "meta": {"입찰추정가격": price}}


def hit(item):
    return {item: {"위반여부": 1, "근거문구": ""}}


class AmountParsing(unittest.TestCase):
    def test_reads_int_float_and_comma_string(self):
        for raw, expected in ((100, 100), (100.9, 100), ("1,234,567", 1234567), (" 250000000 ", 250000000)):
            self.assertEqual(candidate.estimated_price(rec_with(raw)), expected, raw)

    def test_unreadable_amount_is_none(self):
        for raw in (None, "", "   ", "미입력", True, {"a": 1}):
            self.assertIsNone(candidate.estimated_price(rec_with(raw)), raw)

    def test_missing_meta_is_none(self):
        self.assertIsNone(candidate.estimated_price({"id": "X"}))


class Bands(unittest.TestCase):
    def test_v16_band_is_one_hundred_million_to_notice_amount(self):
        """국가 시행령 제21조①10호 나목 + 고시금액. 하한 포함, 상한 미포함."""
        cases = ((99_999_999, False), (100_000_000, True), (229_999_999, True), (230_000_000, False))
        for price, expected in cases:
            self.assertIs(candidate.in_band("v16", price), expected, price)

    def test_v18_band_is_below_one_hundred_million(self):
        for price, expected in ((0, True), (99_999_999, True), (100_000_000, False)):
            self.assertIs(candidate.in_band("v18", price), expected, price)

    def test_ungated_items_always_pass(self):
        """v20 을 포함해 게이트 없는 항목은 금액으로 거르지 않는다."""
        for item in ("v20", "v10", "v11", "v13", "v24"):
            self.assertTrue(candidate.in_band(item, 1))
            self.assertTrue(candidate.in_band(item, 10**12))

    def test_unreadable_amount_does_not_filter(self):
        """금액을 못 읽으면 판정을 지우지 않는다. 결손을 음성 근거로 쓰지 않는다."""
        self.assertTrue(candidate.in_band("v16", None))
        gated = candidate.apply_amount_gate(hit("v16"), rec_with("미입력"))
        self.assertEqual(gated["v16"]["위반여부"], 1)


class Gate(unittest.TestCase):
    def test_out_of_band_positive_becomes_negative(self):
        gated = candidate.apply_amount_gate(hit("v16"), rec_with(50_000_000))
        self.assertEqual(gated["v16"], {"위반여부": 0, "근거문구": ""})

    def test_in_band_positive_survives(self):
        gated = candidate.apply_amount_gate(hit("v16"), rec_with(150_000_000))
        self.assertEqual(gated["v16"]["위반여부"], 1)

    def test_negative_stays_negative_and_input_is_not_mutated(self):
        judgment = {"v16": {"위반여부": 0, "근거문구": ""}}
        gated = candidate.apply_amount_gate(judgment, rec_with(150_000_000))
        self.assertEqual(gated["v16"]["위반여부"], 0)
        judgment["v16"]["위반여부"] = 1
        self.assertEqual(gated["v16"]["위반여부"], 0)

    def test_other_items_pass_through_untouched(self):
        judgment = {"v20": {"위반여부": 1, "근거문구": ""},
                    "v24": {"위반여부": 1, "근거문구": "원문"}}
        gated = candidate.apply_amount_gate(judgment, rec_with(50_000_000))
        self.assertEqual(gated, judgment)


class ReplayStoredRun(unittest.TestCase):
    """보관된 **느슨한** 별도 질의 회차 하나에 게이트를 씌워 1-1 재현값을 지킨다.

    이 클래스가 지키는 것은 그 회차의 값이지 게이트의 일반 성능이 아니다.
    """

    @classmethod
    def setUpClass(cls):
        if not DIAGNOSE.is_file():
            raise unittest.SkipTest(f"{DIAGNOSE} 가 없다")
        cls.rows = load_jsonl(DIAGNOSE)
        cls.amounts = {r["id"]: candidate.estimated_price(r) for r in load_jsonl(DEV)}

    def test_every_dev_notice_has_a_readable_amount(self):
        missing = [rid for rid, amount in self.amounts.items() if amount is None]
        self.assertEqual(missing, [], "금액을 못 읽은 공고")

    def test_gate_reproduces_recorded_counts(self):
        for item, expected in EXPECTED.items():
            tp = fp = fn = 0
            for row in self.rows:
                judged = (row.get("items") or {}).get(item) or {}
                pred = 1 if judged.get("판정") == 1 else 0
                truth = 1 if (row.get("truth") or {}).get(item) == 1 else 0
                if pred and not candidate.in_band(item, self.amounts[row["id"]]):
                    pred = 0
                tp += pred and truth
                fp += pred and not truth
                fn += truth and not pred
            self.assertEqual({"tp": tp, "fp": fp, "fn": fn}, expected, item)

    def test_gate_removes_no_true_positive(self):
        for item in EXPECTED:
            for row in self.rows:
                judged = (row.get("items") or {}).get(item) or {}
                if judged.get("판정") != 1 or (row.get("truth") or {}).get(item) != 1:
                    continue
                self.assertTrue(candidate.in_band(item, self.amounts[row["id"]]),
                                f"{item} 의 TP {row['id']} 를 게이트가 지웠다")


class SubmissionContract(unittest.TestCase):
    """회차 ① 이 제출 CSV 계약을 바꾸지 않는 것을 못 박는다.

    diff 는 모델이 부재탐지 항목에 근거문구를 **생성**하는 것만 허용한다.
    제출되는 것은 여전히 빈칸이어야 한다. 이 검사는 diff 적용 여부와 무관하게
    같은 결과를 내야 하며, diff 를 적용한 채로 돌려도 통과해야 한다.
    """

    @classmethod
    def setUpClass(cls):
        cls.script = candidate.baseline()

    def notice(self):
        """근거문구로 쓸 원문이 실제로 들어 있는 최소 레코드."""
        return {"id": "PPS-TEST-1",
                "docs": [{"doc_id": "d1", "type": "공고문",
                          "text": "입찰참가자격: 중소기업자에 한한다. 기타 사항은 공고문에 따른다."}],
                "meta": {"입찰추정가격": 150_000_000}}

    def model_output_with_absence_evidence(self):
        """모델이 부재탐지 항목에도 인용을 낸 경우. 회차 ① 이 허용하려는 출력이다."""
        out = {}
        for item in self.script.ITEMS:
            out[item] = {"위반여부": 0, "근거문구": None}
        for item in self.script.ABSENCE:
            out[item] = {"위반여부": 1, "근거문구": "입찰참가자격: 중소기업자에 한한다."}
        return out

    def test_postprocess_blanks_absence_evidence_even_when_model_quotes(self):
        done = self.script.postprocess(self.model_output_with_absence_evidence(), self.notice())
        for item in self.script.ABSENCE:
            self.assertEqual(done[item]["위반여부"], 1, item)
            self.assertEqual(done[item]["근거문구"], "", f"{item} 의 e 열이 비어 있지 않다")

    def test_candidate_postprocess_keeps_the_same_contract(self):
        """금액 게이트를 씌워도 부재탐지 e 열은 빈칸이다."""
        done = candidate.postprocess(self.model_output_with_absence_evidence(), self.notice())
        for item in self.script.ABSENCE:
            self.assertEqual(done[item]["근거문구"], "", f"{item} 의 e 열이 비어 있지 않다")

    def test_written_csv_passes_validate_csv(self):
        rec = self.notice()
        done = self.script.postprocess(self.model_output_with_absence_evidence(), rec)
        row = self.script.to_row(rec["id"], done)
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "submission.csv")
            self.script.write_csv([row], path)
            self.assertEqual(self.script.validate_csv(path, [rec["id"]]), [])

    def test_validate_csv_still_rejects_absence_evidence(self):
        """계약을 지키는 쪽뿐 아니라 어기는 쪽도 잡히는지 확인한다."""
        rec = self.notice()
        done = self.script.postprocess(self.model_output_with_absence_evidence(), rec)
        row = self.script.to_row(rec["id"], done)
        row["e" + self.script.ABSENCE[0][1:]] = "입찰참가자격: 중소기업자에 한한다."
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "submission.csv")
            self.script.write_csv([row], path)
            errs = self.script.validate_csv(path, [rec["id"]])
            self.assertTrue(any("부재탐지" in e for e in errs), errs)


class ScriptBinding(unittest.TestCase):
    """후보가 replay_run 이 읽은 제출 코드를 집는지 본다.

    갈라지면 파싱은 `--script` 로 넘긴 코드로, postprocess 는 워킹트리 코드로 돌고
    manifest 에는 아무 흔적이 남지 않는다. 틀린 측정이 후보 탓이 된다.
    """

    def setUp(self):
        self.saved_script = candidate._SCRIPT
        self.saved_submission = sys.modules.get("submission")
        candidate._SCRIPT = None

    def tearDown(self):
        candidate._SCRIPT = self.saved_script
        if self.saved_submission is None:
            sys.modules.pop("submission", None)
        else:
            sys.modules["submission"] = self.saved_submission

    def test_prefers_the_module_replay_run_registered(self):
        stub = types.ModuleType("submission")
        sys.modules["submission"] = stub
        self.assertIs(candidate.baseline(), stub, "저장소 루트의 script.py 를 따로 읽었다")

    def test_falls_back_to_repo_root_when_imported_alone(self):
        sys.modules.pop("submission", None)
        self.assertTrue(hasattr(candidate.baseline(), "ITEMS"))


if __name__ == "__main__":
    unittest.main()
