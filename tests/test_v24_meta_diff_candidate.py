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
        self.assertEqual(replay_run.to_csv_bytes(script, result["rows"]), AFTER.read_bytes(),
                         "지금 후보의 출력이 보관된 candidate-replay/submission.csv 와 다르다")

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
