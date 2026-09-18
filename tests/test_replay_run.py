"""보관된 원응답 재생을 검증한다. 모델을 부르지 않는다."""

import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("replay_run", ROOT / "tools/replay_run.py")
replay_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(replay_run)
SCRIPT = replay_run.load_module(ROOT / "script.py", "submission")

# 원응답이 보관된 유일한 회차. 이 폴더가 없어지면 CPU 재평가 경로 전체가 근거를 잃는다.
CASE = ROOT / "reports/runs/colab-1789655036303880754/dev-debug"
PLAIN_CASE = ROOT / "reports/runs/colab-1789655036303880754/dev"

CANDIDATE = '''"""검사용 후보. 모든 판정을 0으로 만든다."""


def postprocess(judgment, rec):
    return {item: {"위반여부": 0, "근거문구": ""} for item in judgment}
'''


class ReplayRunTests(unittest.TestCase):
    def test_loaded_script_is_reachable_as_sys_modules_submission(self):
        """후보가 이걸로 같은 제출 코드를 집는다. experiments/sme_candidate.baseline() 참고.

        main() 이 다시 돌면 새 모듈로 바뀌므로 모듈 수준 SCRIPT 와 견주지 않는다.
        """
        saved = sys.modules.get("submission")
        try:
            module = replay_run.load_module(ROOT / "script.py", "submission")
            self.assertIs(sys.modules.get("submission"), module)
        finally:
            if saved is None:
                sys.modules.pop("submission", None)
            else:
                sys.modules["submission"] = saved

    def test_failed_load_keeps_the_previous_registration(self):
        """--script 로 없는 경로를 받은 회차가 앞 회차의 제출 코드를 지우면 안 된다.

        main() 은 이 OSError 를 삼키고 1 을 돌려주므로, 지워지면 뒤이은
        sme_candidate.baseline() 이 조용히 워킹트리 script.py 로 되돌아간다.
        """
        saved = sys.modules.get("submission")
        try:
            good = replay_run.load_module(ROOT / "script.py", "submission")
            with self.assertRaises(OSError):
                replay_run.load_module(ROOT / "없는파일.py", "submission")
            self.assertIs(sys.modules.get("submission"), good)
        finally:
            if saved is None:
                sys.modules.pop("submission", None)
            else:
                sys.modules["submission"] = saved

    def test_failed_first_load_leaves_no_registration(self):
        saved = sys.modules.pop("submission", None)
        try:
            with self.assertRaises(OSError):
                replay_run.load_module(ROOT / "없는파일.py", "submission")
            self.assertNotIn("submission", sys.modules)
        finally:
            if saved is not None:
                sys.modules["submission"] = saved

    def test_replay_reproduces_the_run_csv_byte_for_byte(self):
        """이 검사가 빨개지면 재생 결과를 근거로 쓸 수 없다."""
        self.assertTrue(CASE.is_dir(), f"{CASE} 가 없다")
        result = replay_run.replay(SCRIPT, CASE, input_path=ROOT / "open/dev.jsonl",
                                   data_dir=ROOT / "open/data")
        produced = replay_run.to_csv_bytes(SCRIPT, result["rows"])
        self.assertEqual(produced, (CASE / "submission.csv").read_bytes())
        self.assertEqual(len(result["rows"]), 200)
        # 기본 CSV도 같은 응답에서 나오므로 함께 재현돼야 한다.
        self.assertEqual(replay_run.to_csv_bytes(SCRIPT, result["baseline_rows"]),
                         (CASE / "baseline_submission.csv").read_bytes())
        self.assertEqual(len(result["rejected_conditions"]), 107)

    def test_candidate_replaces_only_the_stage_it_defines(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = Path(tmp) / "candidate.py"
            module.write_text(CANDIDATE, encoding="utf-8", newline="\n")
            candidate = replay_run.load_module(module, "candidate")
            self.assertFalse(hasattr(candidate, "verify_sme"), "후보가 verify_sme를 정의하면 안 된다")
            result = replay_run.replay(SCRIPT, CASE, input_path=ROOT / "open/dev.jsonl",
                                       data_dir=ROOT / "open/data",
                                       postprocess=candidate.postprocess)
            produced = replay_run.to_csv_bytes(SCRIPT, result["rows"])
            self.assertNotEqual(produced, (CASE / "submission.csv").read_bytes())
            self.assertTrue(all(row[f"v{i}"] == 0 for row in result["rows"] for i in range(1, 25)))
            # 후보가 안 건드린 단계는 그대로다.
            self.assertEqual(replay_run.to_csv_bytes(SCRIPT, result["baseline_rows"]),
                             (CASE / "baseline_submission.csv").read_bytes())

    def test_refuses_a_case_without_raw_responses(self):
        with self.assertRaisesRegex(ValueError, "원응답이 없다"):
            replay_run.saved_responses(PLAIN_CASE)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "가 없다"):
                replay_run.saved_responses(Path(tmp))

    def test_refuses_a_run_whose_document_budget_shrank(self):
        """줄어든 공고의 실제 예산은 토크나이저가 정했고 로그에 건별 값이 없다."""
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "dev-debug"
            case.mkdir()
            shutil.copy(CASE / "diagnostics.jsonl", case / "diagnostics.jsonl")
            report = json.loads((CASE / "run_report.json").read_text(encoding="utf-8"))
            report["sme_documents_shrunk"] = 3
            (case / "run_report.json").write_text(json.dumps(report, ensure_ascii=False),
                                                  encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "재생할 수 없다"):
                replay_run.replay(SCRIPT, case, input_path=ROOT / "open/dev.jsonl",
                                  data_dir=ROOT / "open/data")

    def test_cli_verify_and_output_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "replay"
            base = ["--case", str(CASE), "--input", str(ROOT / "open/dev.jsonl"),
                    "--data-dir", str(ROOT / "open/data")]
            self.assertEqual(replay_run.main(base + ["--verify"]), 0)
            self.assertEqual(replay_run.main(base + ["--output-dir", str(out)]), 0)
            record = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertIs(record["matches_original"], True)
            self.assertIs(record["model_called"], False)
            self.assertEqual(record["original_sha256"], record["replayed_sha256"])
            self.assertEqual(replay_run.main(base + ["--output-dir", str(out)]), 1, "덮어썼다")

            module = Path(tmp) / "candidate.py"
            module.write_text(CANDIDATE, encoding="utf-8", newline="\n")
            # 후보를 넣고 --verify를 하면 "회차와 같다"는 의미가 사라진다.
            self.assertEqual(replay_run.main(base + ["--verify", "--candidate", str(module)]), 1)


if __name__ == "__main__":
    unittest.main()
