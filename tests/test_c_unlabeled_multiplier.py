"""무라벨 발화 배율 집계기의 경계 검사.

리뷰 [P2] 가 잡은 것: **발화 0건이면 출력에서 `TypeError` 로 죽는다.** 구간은 `미산출` 로
처리했는데 배율 자체가 `None` 인 것을 빼먹어 `:.2f` 가 그대로 먹었다. 그리고 JSON 을 먼저
써서 **죽은 실행이 산출물을 남겼다** — 다음 사람은 그것을 성공한 회차의 것으로 읽는다.

이 검사가 고정하는 것 넷.
  1. dev 발화 0건이어도 안 죽고 `미산출` 로 적는다
  2. 무라벨 발화 0건도 같다
  3. **실패한 실행은 JSON 을 안 남긴다**
  4. 동시 95%(Bonferroni) 구간이 명목보다 넓고, 결론은 동시 쪽이다

모델을 부르지 않는다.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ITEMS = ["v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18", "v20"]
ALL = [f"v{i}" for i in range(1, 25)]


def load_module(name, path):
    """`sys.path` 를 고친 뒤 실어야 하므로 모듈 최상단 import 를 쓰지 않는다."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


multiplier = load_module("c_unlabeled_multiplier",
                         ROOT / "reports/team-c/c-unlabeled-multiplier/multiplier.py")


def write_csv(path, rows):
    header = ["id"] + ALL + [f"e{i}" for i in range(1, 25)]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=header)
        writer.writeheader()
        for row in rows:
            full = {key: "0" for key in header}
            full.update(row)
            writer.writerow(full)


class Interval(unittest.TestCase):
    """구간 계산의 계약."""

    def test_zero_firing_yields_no_interval(self):
        """한쪽이 0 이면 로그법을 못 쓴다. 0 을 넣어 큰 수를 만들지 않는다."""
        self.assertEqual(multiplier.ratio_interval(0, 200, 14, 2000), (None, None))
        self.assertEqual(multiplier.ratio_interval(4, 200, 0, 2000), (None, None))

    def test_direction_is_undecided_without_an_interval(self):
        self.assertEqual(multiplier.direction(None, None), "미정")

    def test_direction_refuses_when_the_interval_spans_one(self):
        self.assertEqual(multiplier.direction(0.12, 1.05), "미정")
        self.assertEqual(multiplier.direction(0.13, 0.57), "더 적다")
        self.assertEqual(multiplier.direction(1.10, 3.00), "더 많다")

    def test_simultaneous_interval_is_wider_than_nominal(self):
        """열 항목을 훑어 고르므로 보정이 필요하다. 보정은 항상 구간을 넓힌다."""
        counts = (9, 200, 24, 2000)
        low, high = multiplier.ratio_interval(*counts)
        sim_low, sim_high = multiplier.ratio_interval(*counts, z=multiplier.Z_SIMULTANEOUS)
        self.assertLess(sim_low, low)
        self.assertGreater(sim_high, high)

    def test_show_writes_none_as_text(self):
        self.assertEqual(multiplier.show(None, ">7.2f"), "미산출")
        self.assertEqual(multiplier.show(0.35, ".2f"), "0.35")


class Methods(unittest.TestCase):
    """리뷰 [P1] 라운드 3 — 결론이 구간 방법에 달려 있으면 안 된다."""

    def test_fisher_matches_scipy(self):
        """`scipy` 없이 짠 정확검정이 참조 구현과 같은가. 다르면 이 표의 결론이 흔들린다."""
        try:
            from scipy.stats import fisher_exact
        except ImportError:
            raise unittest.SkipTest("scipy 가 없다 — 참조 구현과 대조할 수 없다")
        cases = [(12, 369), (5, 98), (4, 28), (11, 537), (9, 56),
                 (5, 38), (6, 53), (11, 189), (3, 311), (5, 183)]
        for dev_k, unl_k in cases:
            mine = multiplier.fisher_two_sided(dev_k, 200, unl_k, 6000)
            reference = fisher_exact([[dev_k, 200 - dev_k], [unl_k, 6000 - unl_k]])[1]
            self.assertAlmostEqual(mine, reference, places=9, msg=(dev_k, unl_k))

    def test_holm_is_monotone_and_bounded(self):
        raw = {"a": 0.001, "b": 0.02, "c": 0.04, "d": 0.5}
        out = multiplier.holm(raw)
        self.assertAlmostEqual(out["a"], 0.004)
        ordered = [out[k] for k in ("a", "b", "c", "d")]
        self.assertEqual(ordered, sorted(ordered))
        self.assertTrue(all(0 <= v <= 1 for v in out.values()))

    def test_holm_is_never_looser_than_bonferroni_for_the_smallest(self):
        raw = {f"v{i}": 0.004 for i in range(10)}
        self.assertAlmostEqual(min(multiplier.holm(raw).values()), 0.04)

    def test_score_interval_brackets_the_point_estimate(self):
        low, high = multiplier.score_interval(9, 200, 56, 6000, multiplier.Z_NOMINAL)
        ratio = (56 / 6000) / (9 / 200)
        self.assertLess(low, ratio)
        self.assertGreater(high, ratio)

    def test_score_interval_is_undefined_at_zero(self):
        self.assertEqual(multiplier.score_interval(0, 200, 56, 6000, 1.96), (None, None))

    def test_agreement_requires_all_three(self):
        """하나라도 다른 말을 하면 미정이다. 이것이 라운드 3 의 수리다."""
        self.assertEqual(multiplier.agreed("더 적다", "더 적다", 0.002), "더 적다")
        # Katz·점수법이 닫아도 Holm 이 안 닫으면 미정 — v15·v16 이 이 경우다
        self.assertEqual(multiplier.agreed("더 적다", "더 적다", 0.1023), "미정")
        # 점수법만 닫는 경우 — v12 가 이 경우다
        self.assertEqual(multiplier.agreed("미정", "더 적다", 0.1118), "미정")
        self.assertEqual(multiplier.agreed("미정", "미정", 0.001), "미정")

    def test_the_two_borderline_items_are_undecided(self):
        """v15·v16 의 실제 수로 고정한다. 셋 중 둘만 닫으므로 방향을 쓰지 않는다."""
        for dev_k, unl_k in ((5, 38), (6, 53)):
            katz = multiplier.direction(*multiplier.ratio_interval(
                dev_k, 200, unl_k, 6000, z=multiplier.Z_SIMULTANEOUS))
            score = multiplier.direction(*multiplier.score_interval(
                dev_k, 200, unl_k, 6000, multiplier.Z_SIMULTANEOUS))
            self.assertEqual(katz, "더 적다", (dev_k, unl_k))
            self.assertEqual(score, "더 적다", (dev_k, unl_k))
            self.assertGreater(multiplier.fisher_two_sided(dev_k, 200, unl_k, 6000) * 9, 0.05)


class ZeroFiringRun(unittest.TestCase):
    """리뷰 [P2] 의 재현 — dev 1행·무라벨 1행, 전 항목 0 발화."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.unlabeled = root / "unl"
        self.unlabeled.mkdir()
        write_csv(self.unlabeled / "u00.csv", [{"id": "PPS-U-1"}])
        self.dev = root / "dev.csv"
        write_csv(self.dev, [{"id": "PPS-DEV-1"}])
        self.labels = root / "labels.csv"
        write_csv(self.labels, [{"id": "PPS-DEV-1"}])
        self.out = root / "multiplier.json"

    def tearDown(self):
        self.tmp.cleanup()

    def run_it(self):
        multiplier.main(["--unlabeled", str(self.unlabeled), "--dev", str(self.dev),
                         "--labels", str(self.labels), "--out", str(self.out)])

    def test_zero_firing_does_not_crash(self):
        self.run_it()                      # 고치기 전에는 여기서 TypeError 였다
        data = json.loads(self.out.read_text(encoding="utf-8"))
        for item in ITEMS:
            row = data["items"][item]
            self.assertIsNone(row["multiplier"], item)
            self.assertIsNone(row["multiplier_low"], item)
            self.assertIsNone(row["score_low"], item)
            self.assertIsNone(row["fisher_p"], item)
            self.assertEqual(row["direction"], "미정", item)
            self.assertEqual(row["katz_direction"], "미정", item)
            self.assertEqual(row["score_direction"], "미정", item)
            self.assertEqual(row["direction_agreed"], "미정", item)

    def test_failed_run_leaves_no_artifact(self):
        """무라벨 공고가 겹치면 죽는다. 그때 JSON 이 남으면 안 된다."""
        write_csv(self.unlabeled / "u01.csv", [{"id": "PPS-U-1"}])   # 같은 id
        with self.assertRaises(SystemExit):
            self.run_it()
        self.assertFalse(self.out.exists(),
                         "실패한 실행이 산출물을 남겼다 — 다음 사람이 성공한 회차로 읽는다")


if __name__ == "__main__":
    unittest.main()
