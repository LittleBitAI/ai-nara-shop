"""v24 플래그 방향 후보 검사. 모델을 부르지 않는다. live 성능 검사가 아니다.

지키는 것은 후보가 끄는 방향이 하나뿐이라는 것이다 — 본문은 지역·업종을 거는데 등록 플래그가
`N` 인 불일치. 등록이 제한인데 집합이 다른 경우와 제목 태그 축은 그대로 양성을 지킨다.
숫자는 회차 `colab-1789902969401579900` 의 `dev-debug` 재생 기준이다.
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
# `submission` 은 후보가 재생 대상 모듈을 찾는 자리다. 카탈로그를 안 채운 채 꽂으면 다른 파일의
# 검사가 품목 조회를 잃는다 — `tests/test_scope_gate_candidate.py` 와 같은 이유다.
script.load_sme_reference(str(ROOT / "open/data"))
candidate = _load("b_v24_flag_direction", ROOT / "experiments" / "b_v24_flag_direction_candidate.py")

BASE = ROOT / "reports" / "team-b" / "b7-v24-fp12"
BEFORE = BASE / "head-replay" / "submission.csv"
AFTER = BASE / "candidate-replay" / "submission.csv"
EXPECTED = {"before": (4, 12, 4), "after": (3, 1, 5)}


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return {row["id"]: row for row in csv.DictReader(stream)}


def records():
    with (ROOT / "open" / "dev.jsonl").open(encoding="utf-8") as stream:
        return {rec["id"]: rec for rec in map(json.loads, stream)}


def v24_after(postprocess, rec):
    judgment = {item: {"위반여부": 0, "근거문구": None} for item in script.ITEMS}
    judgment["v24"] = {"위반여부": 1, "근거문구": None}
    return postprocess(judgment, rec)["v24"]["위반여부"]


class Direction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recs = records()

    def test_flag_n_mismatch_no_longer_holds_a_positive(self):
        for rec_id in ("PPS-DEV-07", "PPS-DEV-044"):   # 지역 N · 업종 N
            with self.subTest(rec_id):
                self.assertEqual(1, v24_after(script.postprocess, self.recs[rec_id]))
                self.assertEqual(0, v24_after(candidate.postprocess, self.recs[rec_id]))

    def test_other_axes_still_hold_a_positive(self):
        # 072 등록 지역 집합 차이 · 057 제목 태그 · 079 등록 업종 목록 밖 코드
        for rec_id in ("PPS-DEV-072", "PPS-DEV-057", "PPS-DEV-079"):
            with self.subTest(rec_id):
                self.assertEqual(1, v24_after(candidate.postprocess, self.recs[rec_id]))

    def test_axes_are_restored_after_the_call(self):
        original = script.AXES
        v24_after(candidate.postprocess, self.recs["PPS-DEV-07"])
        self.assertIs(original, script.AXES)


@unittest.skipUnless(BEFORE.is_file() and AFTER.is_file(), "재생 CSV가 없다. tools/replay_run.py로 먼저 만든다")
class DevReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.truth = read(ROOT / "open" / "dev_labels.csv")
        cls.before = read(BEFORE)
        cls.after = read(AFTER)

    def counts(self, rows):
        pairs = [(self.truth[i]["v24"] == "1", row["v24"] == "1") for i, row in rows.items()]
        return (sum(g and p for g, p in pairs), sum(p and not g for g, p in pairs),
                sum(g and not p for g, p in pairs))

    def test_v24_moves_to_the_recorded_counts(self):
        self.assertEqual(EXPECTED["before"], self.counts(self.before), "기준 재생이 달라졌다")
        self.assertEqual(EXPECTED["after"], self.counts(self.after))

    def test_only_v24_changes_and_only_downward(self):
        for item in script.ITEMS:
            changed = [i for i in self.before if self.before[i][item] != self.after[i][item]]
            if item != "v24":
                self.assertEqual([], changed, f"{item}이 대상 밖인데 바뀌었다")
        raised = [i for i in self.before if self.before[i]["v24"] == "0" and self.after[i]["v24"] == "1"]
        self.assertEqual([], raised)


if __name__ == "__main__":
    unittest.main()
