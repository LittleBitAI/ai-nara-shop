"""v24 메타 대조 후보 검사. 모델을 부르지 않는다. live 성능 검사가 아니다.

여기서 지키는 것은 **필터의 방향**이다. dev 200건 전수로 v24의 TP/FP/FN이 후보의 기준값과
같은지 보고, 대상 밖 23항목의 셀이 하나도 안 바뀌는지 본다. 숫자는 회차
`colab-1789902969401579900`의 `dev-debug` 재생 기준이다 — `dev`와는 다른 추론 회차이므로
`score/metrics.json`의 값과 다르다.

후보는 **내리기만 한다.** 새 양성을 만들지 않으므로 `v24`가 0에서 1로 바뀌는 셀은 없다.
"""

import csv
import importlib.util
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


script = _load("submission", ROOT / "script.py")
# `submission` 이라는 이름은 후보들이 재생 대상 모듈을 찾는 자리다. 카탈로그를 안 채운 채
# 꽂으면 **다른 파일의 검사**가 품목 조회를 잃는다 — `tests/test_scope_gate_candidate.py` 와 같은 이유다.
script.load_sme_reference(str(ROOT / "open/data"))
candidate = _load("v24_meta_diff", ROOT / "experiments" / "a7_v24_meta_diff.py")

BEFORE = ROOT / "reports/runs/colab-1789902969401579900/dev-debug/submission.csv"
AFTER = ROOT / "reports/team-c/a7-v24-meta-diff/candidate-replay/submission.csv"
ITEMS = [f"v{i}" for i in range(1, 25)]

# dev-debug 재생 기준 → 후보. (TP, FP, FN)
EXPECTED = {"before": (5, 36, 3), "after": (4, 12, 4)}
# 축이 어느 공고에서 무엇을 잡아야 하는가. 정답 양성에서 고른 실제 사례다.
AXIS_CASES = {
    "PPS-DEV-057": "계약방법·예산",      # 제목 `(일반경쟁·1억원미만)` 이 등록 계약방법과 다르다
    # 예산 축(`amount_diff`)은 꺼져 있어 여기 없다 — `test_the_amount_axis_is_disabled`.
    "PPS-DEV-071": "지역제한",           # `본점소재지` 제한인데 등록은 지역제한 없음
    "PPS-DEV-072": "지역제한",           # 등록은 `경기도` 하나인데 본문은 "경기도 … 또는 제주도"
    "PPS-DEV-079": "업종",               # 본문 `업종코드: 5210` 이 등록 목록에 없다
}
# 코드가 어느 축으로도 설명하지 못하는 정답 양성. 억지로 살리지 않는다는 것을 고정한다.
UNEXPLAINED = "PPS-DEV-062"


def _rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return {row["id"]: row for row in csv.DictReader(stream)}


def _truth():
    return _rows(ROOT / "open/dev_labels.csv")


def _counts(pred, truth, item):
    tp = fp = fn = 0
    for identifier, row in pred.items():
        hit, gold = row[item] == "1", truth[identifier][item] == "1"
        tp += hit and gold
        fp += hit and not gold
        fn += gold and not hit
    return tp, fp, fn


def _records():
    return {rec["id"]: rec for rec in script.iter_records(str(ROOT / "open/dev.jsonl"))}


class V24MetaDiffCandidate(unittest.TestCase):
    def setUp(self):
        self.before, self.after, self.truth = _rows(BEFORE), _rows(AFTER), _truth()

    def test_the_candidate_still_produces_the_recorded_csv(self):
        """**저장 CSV 를 세기만 하면 가짜 초록이다.** `postprocess` 를 no-op 으로 바꿔도
        4/12/4 와 대상 밖 0셀은 그대로 통과한다. 보관 원응답에 **지금 후보를 적용해**
        바이트 동일인지 본다 — 배선이 끊기면 여기서 빨개진다.
        """
        replay_run = _load("replay_run", ROOT / "tools" / "replay_run.py")
        result = replay_run.replay(script, ROOT / "reports/runs/colab-1789902969401579900/dev-debug",
                                   input_path=str(ROOT / "open/dev.jsonl"),
                                   data_dir=str(ROOT / "open/data"),
                                   postprocess=candidate.postprocess)
        # `company_size_products()`가 검증된 인용을 요구하면서 보관 CSV와 세 셀이 일부러 갈렸다.
        # 보관물을 다시 쓰지 않고 움직인 셀을 고정한다 — 배선이 끊기면 목록이 달라져 빨개진다.
        self.assertEqual(replay_run.csv_cell_diff(replay_run.to_csv_bytes(script, result["rows"]),
                                                  AFTER.read_bytes()),
                         [("PPS-DEV-148", "e13"), ("PPS-DEV-16", "v13"), ("PPS-DEV-198", "v13")],
                         "지금 후보의 출력이 보관된 candidate-replay/submission.csv 와 예상 밖으로 다르다")

    def test_v24_counts_match_the_recorded_replay(self):
        self.assertEqual(_counts(self.before, self.truth, "v24"), EXPECTED["before"])
        self.assertEqual(_counts(self.after, self.truth, "v24"), EXPECTED["after"])

    def test_no_other_item_changes(self):
        changed = [(identifier, item) for identifier in self.before for item in ITEMS
                   if item != "v24" and self.before[identifier][item] != self.after[identifier][item]]
        self.assertEqual(changed, [], "v24 밖의 셀이 바뀌면 이 후보의 범위가 아니다")

    def test_only_lowers_never_raises(self):
        raised = [i for i in self.before
                  if self.before[i]["v24"] == "0" and self.after[i]["v24"] == "1"]
        self.assertEqual(raised, [], "이 후보는 내리기만 한다")

    def test_industry_axis_checks_the_restriction_flag_before_the_code_set(self):
        """등록이 `업종제한여부=N` 인데 본문이 업종을 걸면 그것 자체가 불일치다.

        목록에 같은 코드가 남아 있어 집합 차이가 비면 침묵하던 자리 —
        `region_diff` 가 플래그를 먼저 보는 것과 비대칭이었다.
        """
        clash = {"업종제한여부": "N", "면허업종제한목록": "[학술연구용역(1169)]"}
        self.assertIsNotNone(candidate.industry_diff({}, "입찰참가자격: 업종코드 1169", clash))
        agree = {"업종제한여부": "Y", "면허업종제한목록": "[학술연구용역(1169)]"}
        self.assertIsNone(candidate.industry_diff({}, "업종코드 1169", agree))
        self.assertIsNotNone(candidate.industry_diff({}, "업종코드 5210", agree))

    def test_the_amount_axis_is_disabled(self):
        """예산 축은 **의도적으로 `AXES` 에 없다.** 세 라운드 연속 P1 을 냈다.

        그리고 dev 에서 무력하다 — 남은 발화 3건이 전부 baseline 예측 v24=0 이라
        필터 결과를 한 셀도 안 바꾼다. 축을 빼도 v24 는 `4/12/4` 그대로다.
        항목표가 예산 대조를 명시하므로 **코드는 남긴다.** 재활성화 기준은
        `experiments/a7_v24_meta_diff.py` 의 「왜 예산 축을 껐나」에 있다.
        """
        self.assertEqual(candidate.DISABLED_AXES, ("예산",))
        self.assertNotIn("예산", [name for name, _ in candidate.AXES])
        self.assertIn("계약방법·예산", [name for name, _ in candidate.AXES],
                      "제목 태그의 금액 구간은 다른 기계다 — 그쪽은 남는다")

    def test_the_disabled_amount_axis_still_has_both_known_defects(self):
        """**재활성화의 문턱을 구체적으로 박아 둔다.** 둘 다 무라벨 실측 반례다.

        ① 한 필드의 일치가 다른 필드의 불일치를 지운다.
           `PPS-D-001198`: 기초금액 26,600,000 대 등록 배정 2,660,000 (10배)
           인데 추정가격 24,181,819 ≈ 등록 24,181,818 이라 침묵한다.
        ② `ROUNDING_WON = 1` 이 표시 반올림보다 좁다.
           `PPS-D-000043`: 기초금액 74,460,960 대 등록 배정 74,460,958 (2원, 10원 단위 표시).
        """
        hides = {"배정예산금액": 2_660_000, "입찰추정가격": 24_181_818}
        self.assertIsNone(candidate.amount_diff(
            {}, "기초금액: 금26,600,000원(추정가격 24,181,819원, 부가가치세 2,418,181원)", hides),
            "①이 고쳐졌으면 이 축을 다시 켤 수 있다 — AXES 와 이 검사를 같이 갱신해라")
        rounds = {"배정예산금액": 74_460_958, "입찰추정가격": 67_691_780}
        self.assertIsNotNone(candidate.amount_diff(
            {}, "기초금액: 금74,460,960원(금칠천사백사십육만구백육십원) ※부가가치세 포함", rounds),
            "②가 고쳐졌으면 이 축을 다시 켤 수 있다")

    def test_the_amount_axis_reads_only_the_amount_attached_to_its_label(self):
        """같은 줄의 **부가세**를 예산 불일치로 읽으면 안 된다.

        `PPS-DEV-19` 는 등록 추정가격 168,410,000 과 본문이 정확히 같은데
        `추정가격: 168,410,000원, 부가세: 16,841,000원` 의 뒤 금액까지 비교해 발화했다.
        dev 의 예산 축 발화는 **전부 이 축 단독**이라 오염이 가려지지도 않았다.
        """
        record = _records()["PPS-DEV-19"]
        body = "\n".join(doc["text"] for doc in record["docs"])
        self.assertIsNone(candidate.amount_diff(record, body, record["meta"]))
        # 라벨에 붙은 금액 자체가 등록과 다르면 여전히 발화한다.
        meta = {"배정예산금액": 100_000_000, "입찰추정가격": 90_000_000}
        self.assertIsNotNone(candidate.amount_diff({}, "사업예산: 123,456,789원", meta))

    def test_the_amount_axis_accepts_a_formula_and_rounding_residue(self):
        """등록 금액이 **식 어디에든** 있으면 일치다. ±1원은 부가세 역산의 반올림이다.

        "첫 금액 하나만" 은 절반이었다 — 산식의 구성값을 총액과 비교한다.
        무라벨 `PPS-D-004155`: `사업예산: 1,750,000원 × 18명 = 31,500,000원`,
        등록 배정예산 31,500,000. dev `PPS-DEV-067`: 본문 138,045,454 · 등록 138,045,455.
        """
        formula = {"배정예산금액": 31_500_000, "입찰추정가격": None}
        self.assertIsNone(candidate.amount_diff(
            {}, "사업예산: 1,750,000원 × 18명 = 31,500,000원", formula))
        rounding = {"배정예산금액": 151_850_000, "입찰추정가격": 138_045_455}
        self.assertIsNone(candidate.amount_diff(
            {}, "추정가격 138,045,454원 + 부가가치세 13,804,546원", rounding))
        # 식 어디에도 등록 금액이 없으면 여전히 발화한다.
        self.assertIsNotNone(candidate.amount_diff(
            {}, "사업예산: 123,456,789원", {"배정예산금액": 100_000_000}))

    def test_each_axis_finds_its_case(self):
        records = _records()
        for identifier, axis in AXIS_CASES.items():
            found = candidate.meta_discrepancies(records[identifier])
            self.assertTrue(any(line.startswith(axis) for line in found),
                            f"{identifier}: {axis} 축이 불일치를 못 찾았다 — {found}")

    def test_unexplained_positive_is_not_forced(self):
        """062는 네 축 어디에도 안 걸린다. 그 한 건을 위해 축을 넓히지 않는다."""
        self.assertEqual(candidate.meta_discrepancies(_records()[UNEXPLAINED]), [])
        self.assertEqual(self.after[UNEXPLAINED]["v24"], "0")

    def test_registered_region_matching_the_notice_is_not_a_discrepancy(self):
        """등록 지역과 본문 지역이 같으면 지역 축은 침묵한다 — 새 집합 비교의 반대 방향."""
        records = _records()
        quiet = [i for i, rec in records.items()
                 if (rec.get("meta") or {}).get("지역제한여부") == "Y"
                 and not any(line.startswith("지역제한")
                             for line in candidate.meta_discrepancies(rec))]
        self.assertTrue(quiet, "등록 지역제한 공고 전부가 불일치로 잡히면 비교가 아니라 상수다")


if __name__ == "__main__":
    unittest.main()
