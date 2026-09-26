"""변동폭 집계기의 설정 게이트 — 설정이 갈리면 exit 0 으로 범위를 내지 않는다.

모델을 부르지 않는다.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "reports/runs/colab-1790445336782946136"
_spec = importlib.util.spec_from_file_location(
    "c_variance_aggregate", ROOT / "reports/team-c/c-variance/aggregate.py")
aggregate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aggregate)


class SettingsGate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        for name in ("var-01", "var-02"):
            (self.tmp / name).mkdir()
            for file in ("submission.csv", "run_report.json"):
                shutil.copy(RUN / name / file, self.tmp / name / file)
        self.runs = [str(self.tmp / "var-01"), str(self.tmp / "var-02")]
        self.output = self.tmp / "out.json"

    def change_revision(self):
        path = self.tmp / "var-02/run_report.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        report["model"]["expected_revision"] = "0" * 40
        path.write_text(json.dumps(report), encoding="utf-8")

    def test_same_settings_exit_zero(self):
        self.assertEqual(aggregate.main(["--runs", *self.runs, "--output", str(self.output)]), 0)
        self.assertTrue(json.loads(self.output.read_text(encoding="utf-8"))["settings_identical"])

    def test_mismatch_stops_before_range(self):
        self.change_revision()
        self.assertEqual(aggregate.main(["--runs", *self.runs, "--output", str(self.output)]), 2)
        self.assertFalse(self.output.exists())

    def test_allow_mismatch_still_fails(self):
        self.change_revision()
        code = aggregate.main(["--runs", *self.runs, "--output", str(self.output), "--allow-mismatch"])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(self.output.read_text(encoding="utf-8"))["settings_identical"])


if __name__ == "__main__":
    unittest.main()
