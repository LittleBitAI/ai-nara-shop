"""B9 v24 budget axis candidate. No model call; not a live accuracy check.

Each of the four design conditions guards one notice shape. Undo a condition and the
test named after it goes red. The dev notices come from `open/dev.jsonl`; the two
unlabeled shapes are copied verbatim (the unlabeled file is not in worktrees).
"""

import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


script = sys.modules.get("submission") or _load("submission", ROOT / "script.py")
candidate = _load("b_v24_budget_axis_candidate",
                  ROOT / "experiments" / "b_v24_budget_axis_candidate.py")


def _dev(*ids):
    want, out = set(ids), {}
    with (ROOT / "open/dev.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            rec = json.loads(line)
            if rec["id"] in want:
                out[rec["id"]] = rec
    return out


DEV = _dev("PPS-DEV-29", "PPS-DEV-097", "PPS-DEV-117")


def _rec(text, **meta):
    return {"id": "synthetic", "docs": [{"text": text}], "meta": meta}


# Unlabeled `PPS-D-001198`: base amount is ten times the registered budget, while the
# estimate matches the registered estimate within the VAT back-calculation residual.
FIELD_SHAPE = _rec("나. 용역금액: 금26,600,000원(부가가치세 포함)\n"
                   "다. 기초금액: 금26,600,000원(추정가격 24,181,819원, 부가가치세 2,418,181원)",
                   배정예산금액=2660000, 입찰추정가격=24181818)
# Unlabeled `PPS-D-000043`: the notice shows the registered amount rounded to 10 won.
ROUNDING_SHAPE = _rec("마. 기초금액: 금74,460,960원(금칠천사백사십육만구백육십원) ※부가가치세 포함",
                      배정예산금액=74460958, 입찰추정가격=67691780)


class BudgetAxisTest(unittest.TestCase):
    def test_029_fires_on_both_fields(self):
        found = candidate.budget_mismatch(DEV["PPS-DEV-29"])
        self.assertIsNotNone(found)

    def test_condition1_field_match_does_not_erase_other_field(self):
        self.assertIn("26,600,000", candidate.budget_mismatch(FIELD_SHAPE) or "")

    def test_condition1_other_vat_basis_is_the_same_money(self):
        rec = _rec("가. 사업예산 : 27,200,000 원", 배정예산금액=29920000, 입찰추정가격=27200000)
        self.assertIsNone(candidate.budget_mismatch(rec))

    def test_condition1_estimated_total_is_a_total(self):
        # 국가계약법 시행규칙 제2조제2호: 추정금액 = 추정가격 + 부가가치세 (+ 관급재료).
        rec = _rec("추정금액 : 70,000,000원", 배정예산금액=70000000, 입찰추정가격=63636364)
        self.assertIsNone(candidate.budget_mismatch(rec))

    def test_base_amount_below_the_budget_is_normal(self):
        rec = _rec("차. 사업예산 : 29,920,000원(VAT 포함)\n카. 기초금액 : 29,321,600원(VAT 포함)",
                   배정예산금액=29920000, 입찰추정가격=27200000)
        self.assertIsNone(candidate.budget_mismatch(rec))

    def test_base_amount_above_the_budget_fires(self):
        rec = _rec("마. 기초금액: 금68,237,400원", 배정예산금액=50440000, 입찰추정가격=45854545)
        self.assertIsNotNone(candidate.budget_mismatch(rec))

    def test_condition3_estimated_total_is_a_bid_target(self):
        rec = _rec("□ 사업예산: 294,250,000 원(부가세포함)\nㅇ 추정금액: 284,098,320 원(부가세포함)",
                   배정예산금액=284098320, 입찰추정가격=258271200)
        self.assertIsNone(candidate.budget_mismatch(rec))

    def test_condition4_registered_unit_price_is_not_a_total(self):
        rec = _rec("구매예정금액 : 금 36,900,000원", 배정예산금액=3500, 입찰추정가격=3182)
        self.assertIsNone(candidate.budget_mismatch(rec))

    def test_condition2_display_rounding_is_equal(self):
        self.assertIsNone(candidate.budget_mismatch(ROUNDING_SHAPE))

    def test_condition2_rounding_does_not_swallow_real_gaps(self):
        near = _rec("배정예산: 금74,461,000원", 배정예산금액=74460000)
        self.assertIsNotNone(candidate.budget_mismatch(near))

    def test_condition3_bid_target_beats_project_total(self):
        self.assertIsNone(candidate.budget_mismatch(DEV["PPS-DEV-117"]))

    def test_condition3_project_total_is_compared_when_alone(self):
        alone = _rec("ㅇ 사업예산: 100,000,000원(부가세포함)", 배정예산금액=30000000)
        self.assertIsNotNone(candidate.budget_mismatch(alone))

    def test_condition4_unit_price_contract_compares_the_total(self):
        self.assertIsNone(candidate.budget_mismatch(DEV["PPS-DEV-097"]))

    def test_condition4_total_still_checked_under_unit_price(self):
        rec = _rec("기초금액 : 금2,046,000원\n용역예정금액 : 금90,000,000원(부가세포함)\n"
                   "※ 단가계약 입찰이므로 기초금액을 기준으로 투찰하여야 합니다.",
                   배정예산금액=94035000, 입찰추정가격=85486364)
        self.assertIsNotNone(candidate.budget_mismatch(rec))

    def test_thresholds_are_not_this_notice_price(self):
        rec = _rec("추정가격 230,000,000원 미만인 용역", 입찰추정가격=50000000)
        self.assertIsNone(candidate.budget_mismatch(rec))

    def test_raised_cell_quotes_the_notice(self):
        rec = DEV["PPS-DEV-29"]
        blank = {v: {"위반여부": 0, "근거문구": None} for v in script.ITEMS}
        out = candidate.postprocess(blank, rec)
        base = script.postprocess(blank, rec)
        self.assertEqual(out["v24"]["위반여부"], 1)
        quote = out["v24"]["근거문구"]
        self.assertTrue(any(script.clean_evidence(quote, d["text"]) == quote for d in rec["docs"]))
        self.assertEqual({k: v for k, v in out.items() if k != "v24"},
                         {k: v for k, v in base.items() if k != "v24"})

    def test_silent_notice_is_left_alone(self):
        rec = DEV["PPS-DEV-117"]
        blank = {v: {"위반여부": 0, "근거문구": None} for v in script.ITEMS}
        self.assertEqual(candidate.postprocess(blank, rec), script.postprocess(blank, rec))


if __name__ == "__main__":
    unittest.main()
