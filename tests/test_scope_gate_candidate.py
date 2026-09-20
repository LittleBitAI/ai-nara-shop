"""적용범위 게이트 후보(v6·v9·v23) 검사. 모델을 부르지 않는다. live 성능 검사가 아니다.

여기서 지키는 것은 **게이트의 방향**이다. dev 200건 전수로 세 항목의 TP/FP/FN이 후보의
기준값과 같은지 보고, 대상 밖 21항목의 셀이 하나도 안 바뀌는지 본다.
숫자는 회차 `colab-1789902969401579900`의 `dev-debug` 재생 기준이다 — `dev`와는 다른 추론
회차이므로 `score/metrics.json`의 값과 다르다.
"""

import csv
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


script = _load("submission", ROOT / "script.py")
candidate = _load("scope_gate_candidate", ROOT / "experiments" / "a4_scope_gate_candidate.py")

BASE = ROOT / "reports" / "team-c" / "a4-scope-gate"
BEFORE = BASE / "head-fe30f7e-replay" / "submission.csv"
AFTER = BASE / "candidate-replay" / "submission.csv"
ITEMS = [f"v{i}" for i in range(1, 25)]
TARGET = ("v6", "v9", "v23")
# dev-debug 재생 기준 → 후보. (TP, FP, FN)
EXPECTED = {"v6": ((3, 4, 3), (3, 0, 3)),
            "v9": ((5, 12, 1), (4, 8, 2)),
            "v23": ((1, 1, 4), (2, 1, 3))}


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return {row["id"]: row for row in csv.DictReader(stream)}


def counts(rows, truth, item):
    tp = fp = fn = 0
    for rec_id, row in rows.items():
        gold, got = truth[rec_id][item] == "1", row[item] == "1"
        tp += gold and got
        fp += (not gold) and got
        fn += gold and (not got)
    return tp, fp, fn


def notice(text, *, doc_type="공고문", meta=None):
    return {"id": "sample", "docs": [{"doc_id": "a", "type": doc_type, "text": text}],
            "meta": meta or {}}


class GateDirection(unittest.TestCase):
    """규칙 하나하나가 무엇을 내리고 무엇을 남기는지. 원문 없이 함수만 본다."""

    def test_v6_drops_empty_and_non_region_evidence(self):
        rec = notice("아무 내용")
        self.assertTrue(candidate.v6_not_a_basic_region_limit("", rec))
        self.assertTrue(candidate.v6_not_a_basic_region_limit(
            "본 입찰은 전자입찰로만 집행하며, 전자입찰서는 제출기한 내에 제출하여야 합니다.", rec))

    def test_v6_keeps_a_basic_unit_limit_and_drops_a_wide_expansion(self):
        rec = notice("아무 내용")
        keep = "주된 영업소가 서울특별시 [지역:r1|단위=기초|광역=서울특별시] 내에 소재하고 있는 업체"
        self.assertFalse(candidate.v6_not_a_basic_region_limit(keep, rec))
        drop = "주된 영업소가 입찰공고일 현재 광주광역시, 전라남도의 관할구역 안에 있어야 합니다."
        self.assertTrue(candidate.v6_not_a_basic_region_limit(drop, rec))

    def test_v6_keeps_a_basic_limit_that_also_names_two_wide_regions(self):
        """`PPS-DEV-072`는 정답이 v6과 v7 둘 다 1이다. 광역이 둘이어도 기초 신호가 있으면 남긴다."""
        rec = notice("아무 내용")
        both = "본점 소재지를 계속 경기도 [지역:r1|단위=기초|광역=경기도] 또는 제주도에 둔 업체"
        self.assertFalse(candidate.v6_not_a_basic_region_limit(both, rec))

    def test_v9_keeps_only_quotes_found_in_a_spec_document(self):
        quote = "제조사·모델명 : 터보젯"
        spec = notice(f"규격 안내\n{quote}\n끝", doc_type="규격서")
        self.assertFalse(candidate.v9_not_from_spec_document(quote, spec))
        body = notice(f"공고 본문\n{quote}\n끝", doc_type="공고문")
        self.assertTrue(candidate.v9_not_from_spec_document(quote, body))
        self.assertTrue(candidate.v9_not_from_spec_document("", spec))

    def test_v23_applies_only_to_local_negotiated_contracts(self):
        local = notice("x", meta={"적용계약법": "지방계약법", "낙찰방법": "협상에의한계약"})
        self.assertTrue(candidate.v23_applies(local))
        national = notice("x", meta={"적용계약법": "국가계약법", "낙찰방법": "협상에의한계약"})
        self.assertFalse(candidate.v23_applies(national))
        open_bid = notice("x", meta={"적용계약법": "지방계약법", "낙찰방법": "적격심사제"})
        self.assertFalse(candidate.v23_applies(open_bid))

    def test_v23_fires_below_the_minimum_notice_period_only(self):
        meta = {"적용계약법": "지방계약법", "낙찰방법": "협상에의한계약", "공고게시일자": "20260311"}
        late = notice("현장설명회를 다음과 같이 개최합니다. 일시 : 2026. 3. 18.(수) 14:00", meta=meta)
        self.assertIsNotNone(candidate.v23_late_notice(late))      # 7일 — 최소 8일에 못 미친다
        ontime = notice("현장설명회를 다음과 같이 개최합니다. 일시 : 2026. 3. 19.(목) 14:00", meta=meta)
        self.assertIsNone(candidate.v23_late_notice(ontime))       # 8일 — 적법

    def test_v23_ignores_a_skipped_briefing(self):
        """설명을 안 하면 이 조항이 적용되지 않는다. 뒤에 붙은 제안서 마감일에 걸리면 안 된다."""
        meta = {"적용계약법": "지방계약법", "낙찰방법": "협상에의한계약", "공고게시일자": "20260508"}
        rec = notice("제안요청서 설명회 : 설명회 생략 (제안요청서 교부로 갈음)\n"
                     "라. 제안서 제출 마감 일시 : 2026년 5월 11일 오후 4시까지", meta=meta)
        self.assertIsNone(candidate.v23_late_notice(rec))


@unittest.skipUnless(BEFORE.is_file() and AFTER.is_file(),
                     "재생 CSV가 없다. tools/replay_run.py로 먼저 만든다")
class DevReplay(unittest.TestCase):
    """dev 200건 전수. 표본이 아니라 전부를 돌린다."""

    @classmethod
    def setUpClass(cls):
        cls.truth = read(ROOT / "open" / "dev_labels.csv")
        cls.before = read(BEFORE)
        cls.after = read(AFTER)

    def test_target_items_move_to_the_recorded_counts(self):
        for item, (was, now) in EXPECTED.items():
            with self.subTest(item):
                self.assertEqual(was, counts(self.before, self.truth, item), "기준 재생이 달라졌다")
                self.assertEqual(now, counts(self.after, self.truth, item))

    def test_no_cell_outside_the_three_items_changes(self):
        for item in ITEMS:
            if item in TARGET:
                continue
            changed = [i for i in self.before if self.before[i][item] != self.after[i][item]]
            self.assertEqual([], changed, f"{item}이 대상 밖인데 바뀌었다")

    def test_v10_and_v13_are_untouched_on_purpose(self):
        """열 재료가 없어 A5로 넘긴 둘. 여기서 조용히 손대면 안 된다."""
        for item in ("v10", "v13"):
            with self.subTest(item):
                changed = [i for i in self.before if self.before[i][item] != self.after[i][item]]
                self.assertEqual([], changed)


if __name__ == "__main__":
    unittest.main()
