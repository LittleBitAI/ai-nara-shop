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

    def test_an_unverifiable_setting_in_every_run_is_not_identical(self):
        """모든 통과가 똑같이 비었거나 틀려도 같은 게 아니라 확인 못 한 것이다."""
        cases = {
            "seed absent": (("seed",), None, True),
            "vllm absent": (("environment", "vllm"), None, True),
            "seed null": (("seed",), None, False),
            "revision absent inside model": (("model", "expected_revision"), None, True),
            "revision not a hash": (("model", "expected_revision"), "main", False),
            "seed as text": (("seed",), "20260826", False),
        }
        for label, (path, value, delete) in cases.items():
            with self.subTest(label):
                for name in ("var-01", "var-02"):
                    target = self.tmp / name / "run_report.json"
                    report = json.loads((RUN / name / "run_report.json").read_text(encoding="utf-8"))
                    node = report
                    for key in path[:-1]:
                        node = node[key]
                    if delete:
                        del node[path[-1]]
                    else:
                        node[path[-1]] = value
                    target.write_text(json.dumps(report), encoding="utf-8")
                self.assertEqual(aggregate.main(["--runs", *self.runs]), 2)

    def write(self, name, mutate):
        """`var-02` 의 보고서를 원본에서 새로 써서 한 곳만 바꾼다."""
        report = json.loads((RUN / name / "run_report.json").read_text(encoding="utf-8"))
        mutate(report)
        (self.tmp / name / "run_report.json").write_text(
            json.dumps(report, ensure_ascii=False), encoding="utf-8")

    def test_every_setting_in_the_table_actually_catches_a_drift(self):
        """표의 **모든** 칸이 살아 있는가 — 한 칸만 검사하면 나머지는 장식이다.

        `aggregate.SETTINGS` 를 훑으므로 칸이 늘면 이 검사가 저절로 덮는다. 칸마다
        **형식이 맞으면서 값만 다른** 것을 넣는다. 아무 문자열이나 넣으면 형식 검사에
        걸려 `확인 불가` 가 되고, 그러면 값 비교가 사는지는 확인하지 못한다.
        """
        candidates = ["0" * 64, "f" * 40, "other/model", "9.9.9", 12345, 0.7, True, False]
        for name, (path, valid) in aggregate.SETTINGS.items():
            current = aggregate.dig(
                json.loads((RUN / "var-02/run_report.json").read_text(encoding="utf-8")), path)
            other = next((c for c in candidates if valid(c) and c != current), None)
            with self.subTest(name):
                self.assertIsNotNone(other, f"{name}: 형식이 맞는 다른 값을 못 만들었다")

                def poke(report, path=path, value=other):
                    node = report
                    for key in path[:-1]:
                        node = node.setdefault(key, {})
                    node[path[-1]] = value

                self.write("var-02", poke)
                self.assertEqual(aggregate.main(["--runs", *self.runs]), 2,
                                 f"{name} 이 갈렸는데 집계기가 안 멈췄다")
            self.write("var-02", lambda report: None)   # 다음 칸을 위해 되돌린다

    def test_every_setting_in_the_table_catches_a_missing_value(self):
        """칸을 지우면 `확인 불가` 로 멈춘다. 없는 것을 같다고 읽으면 안 된다."""
        for name, (path, _) in aggregate.SETTINGS.items():
            with self.subTest(name):
                def drop(report, path=path):
                    node = report
                    for key in path[:-1]:
                        node = node.get(key, {})
                    node.pop(path[-1], None)

                self.write("var-02", drop)
                self.assertEqual(aggregate.main(["--runs", *self.runs]), 2,
                                 f"{name} 이 없는데 집계기가 안 멈췄다")
            self.write("var-02", lambda report: None)

    def test_the_table_covers_the_settings_the_report_claims(self):
        """보고서가 적은 묶음이 실제로 표에 있는가 — 문서와 코드가 갈리면 안 된다."""
        expected = {"code_sha256", "input_sha256", "records_sha256", "seed", "temperature",
                    "thinking", "prompt_budget", "max_tokens", "max_chars",      # 최상위 9
                    "model.id", "model.revision", "vllm", "cuda",                # 모델·환경
                    "chat_template_sha256", "sampling_params", "model_dir",
                    "debug_responses"}
        self.assertEqual(set(aggregate.SETTINGS), expected)

    def test_allow_mismatch_still_fails(self):
        self.change_revision()
        code = aggregate.main(["--runs", *self.runs, "--output", str(self.output), "--allow-mismatch"])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(self.output.read_text(encoding="utf-8"))["settings_identical"])


if __name__ == "__main__":
    unittest.main()
