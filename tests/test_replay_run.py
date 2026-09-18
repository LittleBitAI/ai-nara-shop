"""보관된 원응답 재생을 검증한다. 모델을 부르지 않는다."""

import importlib.util
import json
from pathlib import Path
import shutil
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
# 재현은 회차가 실제로 돌린 커밋의 코드로 확인한다. HEAD의 후처리는 바뀔 수 있다.
_SCRATCH = tempfile.TemporaryDirectory()
RUN_SCRIPT = replay_run.run_script(CASE, _SCRATCH.name)

CANDIDATE = '''"""검사용 후보. 모든 판정을 0으로 만든다."""


def postprocess(judgment, rec):
    return {item: {"위반여부": 0, "근거문구": ""} for item in judgment}
'''


class ReplayRunTests(unittest.TestCase):
    def test_replay_reproduces_the_run_csv_byte_for_byte(self):
        """이 검사가 빨개지면 재생 결과를 근거로 쓸 수 없다."""
        self.assertTrue(CASE.is_dir(), f"{CASE} 가 없다")
        result = replay_run.replay(RUN_SCRIPT, CASE, input_path=ROOT / "open/dev.jsonl",
                                   data_dir=ROOT / "open/data")
        produced = replay_run.to_csv_bytes(RUN_SCRIPT, result["rows"])
        self.assertEqual(produced, (CASE / "submission.csv").read_bytes())
        self.assertEqual(len(result["rows"]), 200)
        # 기본 CSV도 같은 응답에서 나오므로 함께 재현돼야 한다.
        self.assertEqual(replay_run.to_csv_bytes(RUN_SCRIPT, result["baseline_rows"]),
                         (CASE / "baseline_submission.csv").read_bytes())
        self.assertEqual(len(result["rejected_conditions"]), 107)

    def test_candidate_replaces_only_the_stage_it_defines(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = Path(tmp) / "candidate.py"
            module.write_text(CANDIDATE, encoding="utf-8", newline="\n")
            candidate = replay_run.load_module(module, "candidate")
            self.assertFalse(hasattr(candidate, "verify_sme"), "후보가 verify_sme를 정의하면 안 된다")
            result = replay_run.replay(RUN_SCRIPT, CASE, input_path=ROOT / "open/dev.jsonl",
                                       data_dir=ROOT / "open/data",
                                       postprocess=candidate.postprocess)
            produced = replay_run.to_csv_bytes(RUN_SCRIPT, result["rows"])
            self.assertNotEqual(produced, (CASE / "submission.csv").read_bytes())
            self.assertTrue(all(row[f"v{i}"] == 0 for row in result["rows"] for i in range(1, 25)))
            # 후보가 안 건드린 단계는 그대로다.
            self.assertEqual(replay_run.to_csv_bytes(RUN_SCRIPT, result["baseline_rows"]),
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
            self.assertEqual(replay_run.main(base + ["--verify", "--output-dir", str(out)]), 0)
            record = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertIs(record["matches_original"], True)
            self.assertIs(record["model_called"], False)
            self.assertEqual(record["original_sha256"], record["replayed_sha256"])
            self.assertEqual(replay_run.main(base + ["--output-dir", str(out)]), 1, "덮어썼다")
            # 후보 없이 --verify를 빼면 HEAD의 script.py로 재생한다(후보 측정의 기준).
            head = Path(tmp) / "head"
            self.assertEqual(replay_run.main(base + ["--output-dir", str(head)]), 0)
            self.assertEqual((head / "submission.csv").read_bytes(), replay_run.to_csv_bytes(
                SCRIPT, replay_run.replay(SCRIPT, CASE, input_path=ROOT / "open/dev.jsonl",
                                          data_dir=ROOT / "open/data")["rows"]))

            module = Path(tmp) / "candidate.py"
            module.write_text(CANDIDATE, encoding="utf-8", newline="\n")
            # 후보를 넣고 --verify를 하면 "회차와 같다"는 의미가 사라진다.
            self.assertEqual(replay_run.main(base + ["--verify", "--candidate", str(module)]), 1)


if __name__ == "__main__":
    unittest.main()
