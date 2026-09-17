"""회차 대조 도구를 모델 없이 검증한다. 합성 CSV만 쓴다."""

import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("compare_runs", ROOT / "tools/compare_runs.py")
compare_runs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compare_runs)
SCORE = compare_runs.load_score()

HEADER = ["id"] + [f"v{i}" for i in range(1, 25)] + [f"e{i}" for i in range(1, 25)]


def write_csv(path, rows):
    """rows: {id: {item_index: value}}. 지정하지 않은 항목은 0이다."""
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(HEADER)
        for identifier, values in rows.items():
            writer.writerow([identifier] + [str(values.get(i, 0)) for i in range(1, 25)] + [""] * 24)
    return path


def ids(count):
    return [f"PPS-DEV-{i:03d}" for i in range(1, count + 1)]


class CompareRunsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        # 정답: 1~4번 공고가 v8 양성, 1~2번이 v24 양성.
        self.truth = write_csv(self.dir / "truth.csv",
                               {i: ({8: 1} if n < 4 else {}) | ({24: 1} if n < 2 else {})
                                for n, i in enumerate(ids(10))})

    def test_reports_per_item_change_and_names_the_flipped_notices(self):
        before = write_csv(self.dir / "before.csv", {i: {} for i in ids(10)})
        # 후보: v8을 2건 맞히고, 대상 밖 v24에서 오탐 1건이 생겼다.
        after = write_csv(self.dir / "after.csv",
                          {i: ({8: 1} if n < 2 else {}) | ({24: 1} if n == 9 else {})
                           for n, i in enumerate(ids(10))})
        result = compare_runs.compare(SCORE, self.truth, before, after, ("v8",))
        rows = {row["item"]: row for row in result["items"]}
        self.assertEqual(rows["v8"]["before"], {"tp": 0, "fp": 0, "fn": 4, "f1": 0.0})
        self.assertEqual(rows["v8"]["after"]["tp"], 2)
        self.assertEqual(rows["v8"]["flipped"], ["PPS-DEV-001", "PPS-DEV-002"])
        self.assertTrue(rows["v8"]["focus"])
        self.assertFalse(rows["v24"]["focus"])
        self.assertEqual(rows["v24"]["flipped"], ["PPS-DEV-010"])
        self.assertEqual(result["changed_cells"], 3)
        self.assertEqual(result["changed_cells_off_focus"], 1, "대상 밖 회귀를 놓쳤다")
        self.assertGreater(result["macro_f1"]["delta"], 0)

        report = compare_runs.render(result)
        self.assertIn("*v8", report)
        self.assertIn("PPS-DEV-010", report)
        self.assertIn("churn", report)
        self.assertIn("reproducibility.md", report)

    def test_identical_runs_report_no_change(self):
        same = write_csv(self.dir / "same.csv", {i: {8: 1} for i in ids(10)})
        result = compare_runs.compare(SCORE, self.truth, same, same)
        self.assertEqual(result["changed_cells"], 0)
        self.assertEqual(result["macro_f1"]["delta"], 0.0)
        self.assertIs(result["drift_reference"]["below_observed_max"], True)
        self.assertNotIn("v8 ", compare_runs.render(result), "변화 없는 항목까지 찍었다")
        self.assertIn("v8", compare_runs.render(result, show_all=True))

    def test_drift_is_reported_as_an_observed_range_not_a_threshold(self):
        """churn의 점수 영향은 관측 쌍마다 수백 배 벌어진다. 범위만 적고 판정하지 않는다."""
        before = write_csv(self.dir / "b2.csv", {i: {} for i in ids(10)})
        after = write_csv(self.dir / "a2.csv",
                          {i: ({8: 1} if n < 1 else {}) for n, i in enumerate(ids(10))})
        result = compare_runs.compare(SCORE, self.truth, before, after)
        reference = result["drift_reference"]
        self.assertLess(reference["macro_f1_min"], reference["macro_f1_max"])
        # 측정을 더할 때마다 상수만 고치면 되도록 여기서 값을 복제하지 않는다.
        self.assertEqual(reference["pairs"], compare_runs.DRIFT_PAIRS)
        self.assertGreaterEqual(reference["pairs"], 5)
        # 한 셀만 맞혀도 지지 4건 항목의 F1이 0.4 올라 관측 범위를 넘는다.
        self.assertFalse(reference["below_observed_max"])
        self.assertIn("관측 범위를 넘는다", compare_runs.render(result))
        # 차이가 범위 안이면 Macro F1만으로 말하지 말라고 찍는다.
        same = write_csv(self.dir / "s2.csv", {i: {} for i in ids(10)})
        inside = compare_runs.compare(SCORE, self.truth, before, same)
        self.assertTrue(inside["drift_reference"]["below_observed_max"])
        self.assertIn("TP/FP/FN", compare_runs.render(inside))

    def test_rejects_mismatched_ids_and_unknown_items(self):
        before = write_csv(self.dir / "b3.csv", {i: {} for i in ids(10)})
        short = write_csv(self.dir / "a3.csv", {i: {} for i in ids(9)})
        with self.assertRaisesRegex(ValueError, "ID 집합이 다르다"):
            compare_runs.compare(SCORE, self.truth, before, short)
        with self.assertRaisesRegex(ValueError, "항목 이름이 아니다"):
            compare_runs.compare(SCORE, self.truth, before, before, ("v8", "v99"))

    def test_cli_writes_a_record_and_refuses_an_existing_directory(self):
        before = write_csv(self.dir / "b4.csv", {i: {} for i in ids(10)})
        after = write_csv(self.dir / "a4.csv",
                          {i: ({8: 1} if n < 2 else {}) for n, i in enumerate(ids(10))})
        out = self.dir / "cmp"
        argv = ["--before", str(before), "--after", str(after), "--truth", str(self.truth),
                "--items", "v8", "--output-dir", str(out)]
        self.assertEqual(compare_runs.main(argv), 0)
        record = json.loads((out / "comparison.json").read_text(encoding="utf-8"))
        self.assertEqual(record["focus"], ["v8"])
        self.assertEqual(record["notices"], 10)
        self.assertIn("v8", (out / "comparison.md").read_text(encoding="utf-8"))
        self.assertEqual(compare_runs.main(argv), 1, "기존 출력 폴더를 덮어썼다")


if __name__ == "__main__":
    unittest.main()
