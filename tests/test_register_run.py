"""결과 ZIP 등록 CLI를 모델·실제 대회 ZIP 없이 검증한다."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("register_run", ROOT / "tools/register_run.py")
register_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(register_run)

COMMIT = "654c556c33144cfa180239872a9ee125b73a5fde"

RUNS_MD = """# 실행 기록

머리말 한 줄.

## 보관 규약

- 폴더는 `reports/runs/<run-id>/`입니다.

## 색인

| run-id | 코드 커밋 | 최종 Macro F1 | 실행 환경 | 원응답 | 폴더 |
| --- | --- | ---: | --- | --- | --- |
| `colab-1` | `aaaaaaa` | 0.1 | 미보관 | 미보관 | — |

꼬리 문장.
"""

RUN_REPORT = {
    "mode": "live",
    "model_success_count": 2,
    "sme_model_success_count": 2,
    "sme_verified_count": 2,
    "sme_rejected_positive_count": 1,
    "sme_fallback_count": 0,
    "sme_documents_shrunk": 0,
    "baseline_inference_seconds": 3.0,
    "sme_inference_seconds": 2.0,
    "input_sha256": "c" * 64,
    "reproduction": {"settings": {"debug_responses": False}},
    "건수": 2,
    "모델로드_s": 10.0,
    "추론_s": 5.0,
    "전체_s": 16.0,
    "유효JSON": 2,
    "메운_항목수": 0,
    "근거_유지": 2,
    "근거_원문불일치_폐기": 1,
    "자가검증": "PASS",
}


def dump(obj):
    return json.dumps(obj, ensure_ascii=False) + "\n"


def results_files(**changes):
    """실제 결과 ZIP과 같은 모양의 작은 가짜 내용. 대회 ZIP은 쓰지 않는다."""
    files = {
        "source.json": dump({"mode": "clone", "url": "https://example.invalid/r.git",
                             "requested_ref": "main", "commit": COMMIT}),
        "runtime.json": dump({"python": "3.12.13", "cuda": "13.0",
                              "gpu": "NVIDIA A100-SXM4-40GB",
                              "packages": {"vllm": "0.26.0", "torch": "2.11.0+cu130"}}),
        "resources.json": dump({"gpus": ["NVIDIA A100-SXM4-40GB, 40960 MiB, 580.82.07"]}),
        "host.json": dump({"python": "3.13.15", "work": "/content/t1-colab-test"}),
        "model.json": dump({"id": "google/gemma-4-26B-A4B-it", "revision": "4d7ae49"}),
        # 오탐 확인: 환경변수 이름·패키지 이름·컨테이너 경로는 값이 아니다.
        "install.log": "hf_xet-1.2.3 설치\n",
        "model-download-command.json": dump({"argv": ["python", "-c", 'os.environ["HF_TOKEN"]'],
                                             "cwd": "/content/t1-colab-test"}),
        "dev.log": "모델 로드 완료   \n",
        "dev-command.json": dump({"argv": ["python", "script.py"], "returncode": 0,
                                  "elapsed_seconds": 16.5}),
        "dev/run_report.json": dump(RUN_REPORT),
        "dev/submission.csv": "id,v1\nA,0\n",
        "score/metrics.json": dump({"macro_f1": 0.2207877, "items": {}}),
        "validation.json": dump({"status": "colab_pass", "macro_f1": 0.2207877}),
    }
    files.update(changes)
    return {name: text for name, text in files.items() if text is not None}


SUBMIT_FILES = {"script.py": "print('t1')\n", "requirements.txt": "\n"}


def write_zip(path, files):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_root(tmp, results=None, submit=None, stem="colab-results-123"):
    root = Path(tmp)
    for folder in ("reports/runs", ".wiki/decisions", "docs", "artifacts/inbox"):
        (root / folder).mkdir(parents=True)
    (root / "docs/runs.md").write_text(RUNS_MD, encoding="utf-8", newline="\n")
    # 자동 생성 결정 기록의 큰 번호는 사람 일련번호가 아니다.
    (root / ".wiki/decisions/2026-09-16-431-4816cf66f.md").write_text("x\n", encoding="utf-8")
    (root / ".wiki/decisions/2026-09-17-016-fix-portable.md").write_text("x\n", encoding="utf-8")
    inbox = root / "artifacts/inbox"
    hashes = {}
    if results is not None:
        hashes["results"] = write_zip(inbox / f"{stem}.zip", results)
    if submit is not None:
        hashes["submit"] = write_zip(inbox / "submit.zip", submit)
    return root, inbox, hashes


class RegisterRunTests(unittest.TestCase):
    def assert_no_trace(self, root):
        """실패한 등록은 부분 결과를 남기지 않는다."""
        self.assertEqual(list((root / "reports/runs").iterdir()), [])
        self.assertEqual((root / "docs/runs.md").read_text(encoding="utf-8"), RUNS_MD)
        self.assertEqual([p.name for p in (root / ".wiki/decisions").glob("*run*")], [])

    def test_registers_one_run_and_writes_index_and_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = results_files()
            root, inbox, hashes = make_root(tmp, files, SUBMIT_FILES)
            summary = register_run.register(inbox, COMMIT, root=root,
                                            expect_results=hashes["results"],
                                            expect_submit=hashes["submit"])
            run = root / "reports/runs/colab-123"
            self.assertEqual(summary["run_id"], "colab-123")
            for name, text in files.items():
                self.assertEqual((run / name).read_bytes(), text.encode("utf-8"), name)
            self.assertFalse((run / "colab-results-123.zip").exists())

            manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["run_id"], "colab-123")
            self.assertEqual(manifest["archive"], "colab-results-123.zip")
            self.assertEqual(manifest["zip_sha256"],
                             {"results": hashes["results"], "submit": hashes["submit"]})
            self.assertEqual(manifest["code"]["commit"], COMMIT)
            self.assertEqual(manifest["environment"]["gpu"], "NVIDIA A100-SXM4-40GB")
            self.assertEqual(manifest["environment"]["cuda"], "13.0")
            self.assertEqual(manifest["environment"]["packages"]["vllm"], "0.26.0")
            self.assertEqual(list(manifest["cases"]), ["dev"])
            self.assertEqual(manifest["cases"]["dev"]["seconds"],
                             {"model_load": 10.0, "baseline_inference": 3.0,
                              "extra_inference": 2.0, "inference_total": 5.0,
                              "run_total": 16.0, "wall_clock": 16.5})
            self.assertEqual(manifest["cases"]["dev"]["counts"]["model_success"], 2)
            self.assertEqual(manifest["cases"]["dev"]["counts"]["extra_rejected_positive"], 1)
            self.assertEqual(manifest["cases"]["dev"]["counts"]["evidence_dropped_not_verbatim"], 1)
            self.assertEqual(manifest["cases"]["dev"]["input_sha256"], "c" * 64)
            self.assertIs(manifest["raw_responses"]["included"], False)
            self.assertEqual(manifest["score"]["final_macro_f1"], 0.2207877)
            self.assertTrue(manifest["registered_at"].endswith("+00:00"))

            index = (root / "docs/runs.md").read_text(encoding="utf-8")
            self.assertIn("| `colab-123` | `654c556` | 0.2207877 | NVIDIA A100-SXM4-40GB, "
                          "vLLM 0.26.0, CUDA 13.0 | 없음 | "
                          "[reports/runs/colab-123/](../reports/runs/colab-123/) |\n", index)
            self.assertLess(index.index("| `colab-1` |"), index.index("| `colab-123` |"))
            self.assertTrue(index.endswith("꼬리 문장.\n"))

            decisions = sorted(p.name for p in (root / ".wiki/decisions").glob("*run-colab-123*"))
            self.assertEqual(len(decisions), 1, decisions)
            self.assertTrue(decisions[0].endswith("-017-run-colab-123.md"), decisions[0])
            draft = (root / ".wiki/decisions" / decisions[0]).read_text(encoding="utf-8")
            self.assertTrue(draft.startswith("---\nscope: project\nseverity: preference\n"))
            for key in ("triggers:", "domain:", "title:"):
                self.assertIn(f"\n{key}", draft)
            body = draft.split("---\n", 2)[2]
            self.assertLess(body.index("# "), body.index("무엇."))
            self.assertLess(body.index("무엇."), body.index("왜."))
            self.assertLess(body.index("왜."), body.index("출처."))
            self.assertNotIn("모델 로드 완료", draft)

    def test_zip_candidates_must_be_exactly_one_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, inbox, _ = make_root(tmp, None, SUBMIT_FILES)
            with self.assertRaisesRegex(ValueError, "colab-results"):
                register_run.register(inbox, COMMIT, root=root)
            self.assert_no_trace(root)
        with tempfile.TemporaryDirectory() as tmp:
            root, inbox, _ = make_root(tmp, results_files(), SUBMIT_FILES)
            write_zip(inbox / "colab-results-456.zip", results_files())
            with self.assertRaisesRegex(ValueError, "2개"):
                register_run.register(inbox, COMMIT, root=root)
            self.assert_no_trace(root)
        with tempfile.TemporaryDirectory() as tmp:
            # submit.zip도 없고 실행이 적어 둔 해시도 없으면 무엇을 제출했는지 알 길이 없다.
            scoreless = results_files(**{"validation.json": dump({"status": "colab_pass"})})
            root, inbox, _ = make_root(tmp, scoreless, None)
            with self.assertRaisesRegex(ValueError, r"submit\.zip"):
                register_run.register(inbox, COMMIT, root=root)
            self.assert_no_trace(root)

    def test_submit_zip_hash_comes_from_the_run_when_the_file_is_withheld(self):
        """품질 게이트 미달이면 노트북이 submit.zip을 안 준다. 그래도 등록은 돼야 한다."""
        recorded = "b" * 64
        withheld = results_files(**{"candidate.json": dump({"submit_sha256": recorded})})
        with tempfile.TemporaryDirectory() as tmp:
            root, inbox, _ = make_root(tmp, withheld, None)
            register_run.register(inbox, COMMIT, root=root, expect_submit=recorded)
            manifest = json.loads(
                (root / "reports/runs/colab-123/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["zip_sha256"]["submit"], recorded)
            self.assertEqual(manifest["zip_sha256_source"]["submit"], "candidate.json")
        with tempfile.TemporaryDirectory() as tmp:
            # 파일이 있으면 실행이 적어 둔 해시와 대조한다. 다른 회차의 ZIP을 붙이면 실패한다.
            root, inbox, _ = make_root(tmp, withheld, SUBMIT_FILES)
            with self.assertRaisesRegex(ValueError, "이 실행이 검증한 ZIP이 아니다"):
                register_run.register(inbox, COMMIT, root=root)
            self.assert_no_trace(root)

    def test_hash_mismatch_fails(self):
        for argument in ("expect_results", "expect_submit"):
            with self.subTest(argument), tempfile.TemporaryDirectory() as tmp:
                root, inbox, _ = make_root(tmp, results_files(), SUBMIT_FILES)
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    register_run.register(inbox, COMMIT, root=root, **{argument: "0" * 64})
                self.assert_no_trace(root)

    def test_missing_expected_paths_fail(self):
        cases = {
            "source.json": dict(results=results_files(**{"source.json": None})),
            "run_report.json": dict(results=results_files(**{"dev/run_report.json": None})),
            "runtime.json": dict(results=results_files(**{"runtime.json": None})),
            "script.py": dict(submit={"requirements.txt": "\n"}),
        }
        for missing, changed in cases.items():
            with self.subTest(missing), tempfile.TemporaryDirectory() as tmp:
                root, inbox, _ = make_root(tmp, changed.get("results", results_files()),
                                           changed.get("submit", SUBMIT_FILES))
                with self.assertRaisesRegex(ValueError, missing.replace(".", r"\.")):
                    register_run.register(inbox, COMMIT, root=root)
                self.assert_no_trace(root)

    def test_commit_must_match_the_recorded_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, inbox, _ = make_root(tmp, results_files(), SUBMIT_FILES)
            with self.assertRaisesRegex(ValueError, "커밋"):
                register_run.register(inbox, "9" * 40, root=root)
            self.assert_no_trace(root)

    def test_secret_patterns_fail(self):
        payloads = {
            "HF_TOKEN": "HF_TOKEN=hf_AbCdEfGhIjKlMnOpQrStUvWxYz012345\n",
            "hf_": '{"token": "hf_AbCdEfGhIjKlMnOpQrStUvWxYz012345"}\n',
            "api_key": '{"api_key": "sk-live-0123456789abcdef"}\n',
            "Bearer": "authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abcdefgh\n",
            "windows-path": "C:\\Users\\dasdk\\PycharmProjects\\ai-nara-shop\\out.csv\n",
            "posix-path": "/home/someone/work/results/submission.csv\n",
        }
        for name, payload in payloads.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                root, inbox, _ = make_root(tmp, results_files(**{"leak.log": payload}), SUBMIT_FILES)
                with self.assertRaisesRegex(ValueError, r"leak\.log"):
                    register_run.register(inbox, COMMIT, root=root)
                self.assert_no_trace(root)

    def test_documented_false_positives_do_not_fail(self):
        """docs/runs.md가 정한 경계: 값이 붙은 것만 위반이다. 헛되이 빨개지면 아무도 안 쓴다."""
        freeze = ("hf-xet==1.6.0\ntokenizers==0.22.2\ntiktoken==0.14.0\n"
                  "tokenspeed-mla==0.1.8\ncuda-pathfinder==1.8.1\n")
        install = ("Downloading hf_xet-1.6.0-cp312-cp312-manylinux_2_28_x86_64.whl\n"
                   "Collecting tokenizers>=0.21.1 (from vllm==0.26.0)\n")
        notebook = ('token=os.environ["HF_TOKEN"]\nenv = {"HF_TOKEN": token}\n'
                    '"HF_TOKEN": "***"\nargv = ["--api-key", "--expect-results"]\n'
                    "The Authorization header uses the Bearer scheme.\n")
        colab = ("/content/t1-colab-7jprh479/cases/dev/data/test.jsonl.gz\n"
                 "/root/.cache/huggingface/hub/models--google--gemma-4-26B-A4B-it/snapshots/4d7ae49\n")
        rule = ("등록 전에 `HF_TOKEN`·`hf_`·`api_key`·`Bearer`·개인 절대 경로 패턴을 검사합니다.\n"
                "값이 붙은 것만 위반입니다. 환경변수 이름, `hf_xet` 같은 패키지 이름은 오탐입니다.\n")
        payloads = {"pip-freeze.log": freeze, "install.log": install,
                    "model-download-command.json": notebook, "paths.log": colab, "rule.log": rule}
        with tempfile.TemporaryDirectory() as tmp:
            root, inbox, _ = make_root(tmp, results_files(**payloads), SUBMIT_FILES)
            register_run.register(inbox, COMMIT, root=root)
            run = root / "reports/runs/colab-123"
            for name, text in payloads.items():
                self.assertEqual((run / name).read_text(encoding="utf-8"), text, name)

    def test_index_keeps_existing_rows_and_leaves_the_score_blank(self):
        """⑥ 새 행 하나만 붙는다. 로그에 점수가 없으면 재계산하지 않고 빈칸으로 둔다."""
        live = (ROOT / "docs/runs.md").read_text(encoding="utf-8")
        before = [line for line in live.splitlines() if line.startswith("| `colab-")]
        with tempfile.TemporaryDirectory() as tmp:
            scoreless = results_files(**{"score/metrics.json": None, "validation.json": None})
            root, inbox, _ = make_root(tmp, scoreless, SUBMIT_FILES)
            (root / "docs/runs.md").write_text(live, encoding="utf-8", newline="\n")
            register_run.register(inbox, COMMIT, root=root)
            after = [line for line in (root / "docs/runs.md").read_text(encoding="utf-8").splitlines()
                     if line.startswith("| `colab-")]
            self.assertEqual(after[:len(before)], before, "기존 행이 바뀌었다")
            self.assertEqual(len(after), len(before) + 1)
            self.assertEqual(after[-1].split("|")[3], "  ", f"점수 칸이 비어 있지 않다: {after[-1]}")
            manifest = json.loads((root / "reports/runs/colab-123/manifest.json").read_text(encoding="utf-8"))
            self.assertIsNone(manifest["score"]["final_macro_f1"])
            self.assertIsNone(manifest["cases"]["dev"]["macro_f1"])

    def test_cli_exits_nonzero_and_leaves_nothing_for_each_failure(self):
        """⑤ 훅이 아니라 CLI로 만든 이유. 다섯 실패가 실제로 종료 코드 0이 아니어야 한다."""
        def cli(root, inbox, **extra):
            argv = ["--inbox", str(inbox), "--code-commit", COMMIT, "--root", str(root)]
            for key, value in extra.items():
                argv += [f"--{key}", value]
            return register_run.main(argv)

        with tempfile.TemporaryDirectory() as tmp:  # 해시 불일치
            root, inbox, _ = make_root(tmp, results_files(), SUBMIT_FILES)
            self.assertEqual(cli(root, inbox, **{"expect-results": "0" * 64}), 1)
            self.assert_no_trace(root)
        with tempfile.TemporaryDirectory() as tmp:  # 후보 0개
            root, inbox, _ = make_root(tmp, None, SUBMIT_FILES)
            self.assertEqual(cli(root, inbox), 1)
            self.assert_no_trace(root)
        with tempfile.TemporaryDirectory() as tmp:  # 후보 2개
            root, inbox, _ = make_root(tmp, results_files(), SUBMIT_FILES)
            write_zip(inbox / "colab-results-456.zip", results_files())
            self.assertEqual(cli(root, inbox), 1)
            self.assert_no_trace(root)
        with tempfile.TemporaryDirectory() as tmp:  # zip slip
            root, inbox, _ = make_root(tmp, results_files(**{"../escape.log": "x\n"}), SUBMIT_FILES)
            self.assertEqual(cli(root, inbox), 1)
            self.assert_no_trace(root)
            self.assertFalse((root.parent / "escape.log").exists())
        with tempfile.TemporaryDirectory() as tmp:  # 50MB 초과
            huge = "0" * (register_run.MAX_FILE_BYTES + 1)
            root, inbox, _ = make_root(tmp, results_files(**{"huge.log": huge}), SUBMIT_FILES)
            self.assertEqual(cli(root, inbox), 1)
            self.assert_no_trace(root)
        with tempfile.TemporaryDirectory() as tmp:  # 기존 run-id 재등록
            root, inbox, _ = make_root(tmp, results_files(), SUBMIT_FILES)
            self.assertEqual(cli(root, inbox), 0)
            kept = {p: p.read_bytes() for p in (root / "reports/runs/colab-123").rglob("*") if p.is_file()}
            index = (root / "docs/runs.md").read_text(encoding="utf-8")
            self.assertEqual(cli(root, inbox), 1, "같은 run-id 재등록이 통과했다")
            self.assertEqual({p: p.read_bytes() for p in (root / "reports/runs/colab-123").rglob("*")
                              if p.is_file()}, kept)
            self.assertEqual((root / "docs/runs.md").read_text(encoding="utf-8"), index)
            self.assertEqual(len(list((root / ".wiki/decisions").glob("*run-colab-123*"))), 1)

    def test_single_file_over_the_limit_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            oversized = "0" * (register_run.MAX_FILE_BYTES + 1)
            root, inbox, _ = make_root(tmp, results_files(**{"huge.log": oversized}), SUBMIT_FILES)
            with self.assertRaisesRegex(ValueError, r"huge\.log"):
                register_run.register(inbox, COMMIT, root=root)
            self.assert_no_trace(root)

    def test_zip_slip_fails(self):
        for name in ("../escape.log", "/etc/escape.log", "dev/../../escape.log"):
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                root, inbox, _ = make_root(tmp, results_files(**{name: "x\n"}), SUBMIT_FILES)
                with self.assertRaisesRegex(ValueError, "대상 디렉터리 밖"):
                    register_run.register(inbox, COMMIT, root=root)
                self.assert_no_trace(root)
                self.assertFalse((root.parent / "escape.log").exists())

    def test_existing_run_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, inbox, _ = make_root(tmp, results_files(), SUBMIT_FILES)
            kept = root / "reports/runs/colab-123/manifest.json"
            kept.parent.mkdir(parents=True)
            kept.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "colab-123"):
                register_run.register(inbox, COMMIT, root=root)
            self.assertEqual(kept.read_text(encoding="utf-8"), "{}\n")
            self.assertEqual((root / "docs/runs.md").read_text(encoding="utf-8"), RUNS_MD)

    def test_existing_index_row_is_filled_in_not_duplicated(self):
        """`미보관`으로 이미 적힌 실행을 등록하면 행이 두 개가 되면 안 된다."""
        with tempfile.TemporaryDirectory() as tmp:
            root, inbox, _ = make_root(tmp, results_files(), SUBMIT_FILES, stem="colab-results-1")
            register_run.register(inbox, COMMIT, root=root)
            index = (root / "docs/runs.md").read_text(encoding="utf-8")
            rows = [line for line in index.splitlines() if line.startswith("| `colab-1` |")]
            self.assertEqual(len(rows), 1, rows)
            self.assertIn("0.2207877", rows[0])
            self.assertTrue(index.endswith("꼬리 문장.\n"))

    def test_repository_index_keeps_the_anchor_and_the_command(self):
        """색인 표 머리글은 등록 도구가 행을 끼우는 자리다. 명령은 문서에 적혀 있어야 한다."""
        index = (ROOT / "docs/runs.md").read_text(encoding="utf-8")
        self.assertIn(f"\n{register_run.INDEX_HEADER}", index)
        self.assertIn("python -X utf8 tools/register_run.py", index)
        self.assertIn(register_run.COMMAND,
                      (ROOT / ".wiki/adapter.toml").read_text(encoding="utf-8"))

    def test_cli_returns_nonzero_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, inbox, _ = make_root(tmp, None, SUBMIT_FILES)
            code = register_run.main(["--inbox", str(inbox), "--code-commit", COMMIT,
                                      "--root", str(root)])
            self.assertEqual(code, 1)
            self.assert_no_trace(root)


if __name__ == "__main__":
    unittest.main()
