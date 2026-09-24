"""제출 ZIP과 Colab 실행 경로를 모델 없이 검증한다."""

import ast
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from types import ModuleType, SimpleNamespace
import unittest
import venv
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_tool", ROOT / "tools/package.py")
package_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package_tool)
NOTEBOOK = json.loads((ROOT / "notebooks/colab-baseline.ipynb").read_text(encoding="utf-8"))
CELLS = {cell["id"]: "".join(cell["source"]) for cell in NOTEBOOK["cells"] if cell["cell_type"] == "code"}


def notebook_functions():
    # Execute the notebook's actual logging helpers, without a Colab or GPU dependency.
    tree = ast.parse(CELLS["setup"])
    functions = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)], type_ignores=[])
    return compile(functions, "colab-helpers", "exec")


class PackageTests(unittest.TestCase):
    def test_clone_prepares_bundle_from_recorded_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            results = work / "results"
            results.mkdir()
            namespace = dict(WORK=work, RESULTS=results, SOURCE_MODE="clone", REPO_URL=str(ROOT),
                             REPO_REF="main", sys=sys, subprocess=subprocess, Path=Path,
                             json=json, time=time, os=os, PYTHON=str(work / "venv/bin/python"))
            exec(notebook_functions(), namespace)
            with patch("builtins.print"):
                exec(compile(CELLS["clone"], "colab-clone", "exec"), namespace)
            source = json.loads((results / "source.json").read_text())
            actual = subprocess.check_output(["git", "rev-parse", "main"], cwd=ROOT, text=True).strip()
            self.assertEqual(source["commit"], actual)
            with zipfile.ZipFile(namespace["BUNDLE_PATH"]) as bundle:
                with zipfile.ZipFile(io.BytesIO(bundle.read("submit.zip"))) as submit:
                    expected = subprocess.check_output(["git", "show", actual + ":script.py"], cwd=ROOT)
                    self.assertEqual(submit.read("script.py"), expected)

    def test_colab_requires_token_and_passes_it_only_to_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            calls = []
            namespace = dict(WORK=work, RESULTS=work, PYTHON=sys.executable, MODEL_ID="test-model",
                             REVISION="test-revision", os=os, Path=Path, json=json)
            exec(notebook_functions(), namespace)
            colab = ModuleType("google.colab")
            colab.userdata = SimpleNamespace(get=lambda name: "", SecretNotFoundError=KeyError,
                                            NotebookAccessError=PermissionError)
            namespace["run_logged"] = lambda *args, **kwargs: calls.append((args, kwargs))
            with patch.dict(sys.modules, {"google.colab": colab}), patch("getpass.getpass", return_value=""):
                with self.assertRaisesRegex(ValueError, "HF_TOKEN"):
                    exec(compile(CELLS["download"], "colab-download", "exec"), namespace)
            self.assertEqual(calls, [])

            colab.userdata.get = lambda name: "test-secret-token"
            hub = ModuleType("huggingface_hub")
            def download(**kwargs):
                calls.append(kwargs)
                return str(work / "test-revision")
            hub.snapshot_download = download
            def run_download(name, command, env):
                self.assertNotIn("test-secret-token", json.dumps(command))
                self.assertEqual(env["HF_TOKEN"], "test-secret-token")
                with patch.dict(os.environ, env, clear=True), patch.object(sys, "argv", ["-c", *command[3:]]), \
                        patch.dict(sys.modules, {"huggingface_hub": hub}):
                    exec(compile(command[2], "download-subprocess", "exec"), {})
            namespace["run_logged"] = run_download
            with patch.dict(sys.modules, {"google.colab": colab}):
                exec(compile(CELLS["download"], "colab-download", "exec"), namespace)
            self.assertEqual(calls[0]["token"], "test-secret-token")
            self.assertEqual(calls[0]["revision"], "test-revision")
            self.assertNotIn("HF_TOKEN", namespace["download_env"])
            self.assertIsNone(namespace["token"])
            self.assertNotIn("test-secret-token", (work / "model.json").read_text())

    def test_colab_bundle_runs_exact_submission_and_rejects_bad_archive(self):
        for identifier, source in CELLS.items():
            compile(source, identifier, "exec")
        for node in ast.parse(CELLS["install"]).body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "runtime_code" for t in node.targets):
                compile(ast.literal_eval(node.value), "runtime-subprocess", "exec")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            submission, bundle = tmp / "submit.zip", tmp / "colab-bundle.zip"
            package_tool.package(submission)
            manifest = package_tool.package_colab(bundle, submission)
            self.assertFalse(manifest["live_verified"])
            original = bundle.read_bytes()
            with self.assertRaises(FileExistsError):
                package_tool.package_colab(bundle, submission)
            self.assertEqual(bundle.read_bytes(), original)
            work = tmp / "work"
            results = work / "results"
            results.mkdir(parents=True)
            namespace = dict(WORK=work, RESULTS=results, MODEL_ID="test", REVISION="test",
                             SOURCE_MODE="upload",
                             Path=Path, io=io, json=json, zipfile=zipfile, hashlib=hashlib,
                             time=time, subprocess=subprocess, os=os, shutil=shutil, gzip=gzip, csv=csv,
                             PYTHON=sys.executable, MODEL_DIR=str(work / "models/test"),
                             SERVER_PYTHON="3.12.13", case_inputs={},
                             EXPECTED_PACKAGES={"vllm": "0.26.0", "torch": "2.11.0+cu130",
                                                "transformers": "5.14.1", "xgrammar": "0.2.3"})
            exec(notebook_functions(), namespace)
            colab = ModuleType("google.colab")
            colab.files = SimpleNamespace(upload=lambda: {"colab-bundle.zip": bundle.read_bytes()})
            with patch.dict(sys.modules, {"google.colab": colab}):
                exec(compile(CELLS["upload"], "colab-upload", "exec"), namespace)
            extracted = namespace["SUBMISSION"] / "script.py"
            self.assertEqual(extracted.read_bytes(), (ROOT / "script.py").read_bytes())
            completed = subprocess.run([sys.executable, "-X", "utf8", str(extracted), "--mock",
                "--data-dir", str(work / "open/data"), "--output-dir", str(results / "mock")],
                capture_output=True, timeout=30)
            self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8"))
            functions = ast.Module(body=[n for n in ast.parse(CELLS["sample"]).body
                                        if isinstance(n, ast.FunctionDef)], type_ignores=[])
            exec(compile(functions, "colab-live-check", "exec"), namespace)
            with self.assertRaisesRegex(RuntimeError, "실제 모델 성공"):
                namespace["check_live"]("mock", 10)
            real_popen = subprocess.Popen
            def mock_model_only(command, **kwargs):
                self.assertEqual(command, [sys.executable, "script.py"])
                self.assertNotIn("PPS_QUANT", kwargs["env"])
                self.assertNotIn("HF_TOKEN", kwargs["env"])
                self.assertEqual(kwargs["env"]["HF_HUB_OFFLINE"], "1")
                # The notebook command remains unmodified; this test substitutes model-free execution.
                return real_popen([command[0], "-X", "utf8", command[1], "--mock"], **kwargs)
            with patch.dict(os.environ, {"PPS_QUANT": "wrong", "HF_TOKEN": "test-token"}), \
                    patch("subprocess.Popen", side_effect=mock_model_only), patch("builtins.print"):
                namespace["run_case"]("sample", work / "open/data/test.jsonl.gz")
                namespace["run_case"]("dev", work / "open/dev.jsonl")
            with gzip.open(work / "cases/dev/data/test.jsonl.gz", "rb") as compressed:
                self.assertEqual(compressed.read(), (work / "open/dev.jsonl").read_bytes())
            # 같은 입력은 회차마다 같은 .gz 바이트여야 input_sha256으로 두 회차를 대조할 수 있다.
            with patch("subprocess.Popen", side_effect=mock_model_only), patch("builtins.print"):
                namespace["run_case"]("dev-again", work / "open/dev.jsonl")
            self.assertEqual((work / "cases/dev/data/test.jsonl.gz").read_bytes(),
                             (work / "cases/dev-again/data/test.jsonl.gz").read_bytes())
            self.assertEqual(namespace["case_inputs"]["dev"], namespace["case_inputs"]["dev-again"])
            # 진단 도구가 번들이 만든 배치에서 실제로 실행되는지 본다.
            # 스텁으로 인자만 확인하면 경로가 없다는 것을 못 잡는다 — 실제로 한 번 잡혔다.
            tool = work / "tools/diagnose_items.py"
            self.assertTrue(tool.is_file(), "번들에 tools/diagnose_items.py가 없다")
            with (work / "open/dev.jsonl").open(encoding="utf-8") as stream:
                sample_ids = [json.loads(line)["id"] for line in stream][:2]
            diagnose = subprocess.run(
                [sys.executable, "-X", "utf8", str(tool), "--items", "v16,v18", "--mock",
                 "--ids", ",".join(sample_ids), "--script", str(namespace["SUBMISSION"] / "script.py"),
                 "--input", str(work / "open/dev.jsonl"), "--data-dir", str(work / "open/data"),
                 "--labels", str(work / "open/dev_labels.csv"),
                 "--output-dir", str(results / "diagnose-smoke")],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
            self.assertEqual(diagnose.returncode, 0, diagnose.stderr)
            record = json.loads((results / "diagnose-smoke/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(record["notice_count"], 2)
            self.assertEqual(record["script_sha256"],
                             hashlib.sha256((ROOT / "script.py").read_bytes()).hexdigest())
            report_path = results / "dev/run_report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            # Synthetic success metadata exercises the gate only, never a live-model result.
            report.update(mode="live", model_success_count=200, sme_model_success_count=0,
                          model={"id": "test", "expected_revision": "test"})
            report["environment"]["cuda"] = "13.0"
            report["reproduction"].update(python="3.12.13", packages=namespace["EXPECTED_PACKAGES"].copy())
            def write():
                report_path.write_text(json.dumps(report), encoding="utf-8")
            write()
            namespace["check_live"]("dev", 200)
            baseline_path = results / "dev/baseline_submission.csv"
            original_baseline = baseline_path.read_bytes()
            with baseline_path.open(encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            # Synthetic CSV changes exercise the live gate, not model accuracy.
            # v13 is zero: A1 may still change each of its own value/evidence columns.
            for item in ("v14", "v15", "v16", "v17", "v18"):
                changed_rows = [dict(row) for row in rows]
                changed_rows[0][item] = "1"
                changed_rows[0]["e" + item[1:]] = "" if item in ("v16", "v18") else "기업등급 제한"
                with baseline_path.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(changed_rows)
                namespace["check_live"]("dev", 200)
            baseline_path.write_bytes(original_baseline)
            final_path = results / "dev/submission.csv"
            original_final = final_path.read_bytes()
            changed_rows = list(csv.DictReader(io.StringIO(original_final.decode("utf-8"))))
            changed_rows[0].update(v13="1", e13="기업등급 제한")
            with final_path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=changed_rows[0].keys())
                writer.writeheader()
                writer.writerows(changed_rows)
            # A1 scope owns v13 even when the selective SME call skipped this notice.
            # Check both shipping notebooks against the same changed CSV.
            for notebook in ("colab-baseline.ipynb", "exp-a3-source-role.ipynb"):
                # The A3 notebook is pinned to 18f07e5, which runs with thinking off; present it the
                # settings that code writes. colab-baseline checks the current code's settings.
                settings = report["reproduction"]["settings"]
                if notebook == "exp-a3-source-role.ipynb":
                    settings["thinking"] = False
                    settings.pop("baseline_thinking_token_budget", None)
                    write()
                nb = json.loads((ROOT / "notebooks" / notebook).read_text(encoding="utf-8"))
                source = next("".join(c["source"]) for c in nb["cells"] if c["id"] == "sample")
                check = next(n for n in ast.parse(source).body
                             if isinstance(n, ast.FunctionDef) and n.name == "check_live")
                exec(compile(ast.Module(body=[check], type_ignores=[]), notebook, "exec"), namespace)
                namespace["check_live"]("dev", 200)
                owners = report["reproduction"]["settings"]["extra_call_items"]
                owners["company_size"].remove("v13")
                write()
                with self.assertRaisesRegex(RuntimeError, "생략한 공고"):
                    namespace["check_live"]("dev", 200)
                owners["company_size"].append("v13")
                write()
            final_path.write_bytes(original_final)
            # Keep an A1-only change for the missing ownership-map failure below.
            with baseline_path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows([dict(row, v18="1") if i == 0 else row for i, row in enumerate(rows)])
            owned = report["reproduction"]["settings"].pop("extra_call_items")
            write()
            with self.assertRaisesRegex(RuntimeError, "대상 밖"):
                namespace["check_live"]("dev", 200)
            report["reproduction"]["settings"]["extra_call_items"] = owned
            write()
            baseline_path.write_bytes(original_baseline)
            rows[0]["v13"] = "1"
            def write_baseline():
                with baseline_path.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
            write_baseline()
            with self.assertRaisesRegex(RuntimeError, "선택 건수"):
                namespace["check_live"]("dev", 200)
            # An optional failure is accepted only with full baseline success and exact counts.
            report.update(sme_selected_count=1, sme_skipped_count=199,
                          sme_model_success_count=0, sme_verified_count=0, sme_fallback_count=1)
            final_path = results / "dev/submission.csv"
            original_final = final_path.read_bytes()
            final_path.write_bytes(baseline_path.read_bytes())
            write()
            namespace["check_live"]("dev", 200)
            report["model_success_count"] = 199
            write()
            with self.assertRaisesRegex(RuntimeError, "실제 모델 성공"):
                namespace["check_live"]("dev", 200)
            report.update(model_success_count=200, sme_fallback_count=0)
            write()
            with self.assertRaisesRegex(RuntimeError, "실제 모델 성공"):
                namespace["check_live"]("dev", 200)
            report.update(sme_selected_count=0, sme_skipped_count=200,
                          sme_model_success_count=0, sme_verified_count=0)
            write()
            baseline_path.write_bytes(original_baseline)
            final_path.write_bytes(original_final)
            with final_path.open(encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            rows[0]["v13"] = "1"
            write_baseline()
            final_path.write_bytes(baseline_path.read_bytes())
            baseline_path.write_bytes(original_baseline)
            # With no other phase owning v13, skipped-SME preservation still applies.
            report["reproduction"]["settings"]["extra_call_items"]["company_size"].remove("v13")
            write()
            with self.assertRaisesRegex(RuntimeError, "생략한 공고"):
                namespace["check_live"]("dev", 200)
            report["reproduction"]["settings"]["extra_call_items"]["company_size"].append("v13")
            write()
            final_path.write_bytes(original_final)
            with baseline_path.open(encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            rows[0]["e1"] = "unexpected change"
            with baseline_path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(RuntimeError, "대상 밖"):
                namespace["check_live"]("dev", 200)
            baseline_path.write_bytes(original_baseline)
            downloaded = []
            colab.files.download = downloaded.append
            # Real scoring of mock CSVs must not export a non-improving ZIP.
            check_live = namespace["check_live"]
            namespace["check_live"] = lambda *args: report
            try:
                with patch.dict(sys.modules, {"google.colab": colab}), patch("builtins.print"):
                    exec(compile(CELLS["score"], "colab-score", "exec"), namespace)
            finally:
                namespace["check_live"] = check_live
            self.assertEqual(downloaded, [])
            self.assertFalse(namespace["quality_pass"])
            # Exercise export thresholds with synthetic metrics, never a GPU result.
            tail = CELLS["score"][CELLS["score"].index("baseline_f1 ="):]
            for candidate, paired, allowed in [(0.21, 0.2, False), (0.3, 0.3, False), (0.3, 0.2, True)]:
                namespace["metrics"]["macro_f1"] = candidate
                namespace["paired_metrics"]["macro_f1"] = paired
                downloaded.clear()
                with patch.dict(sys.modules, {"google.colab": colab}), patch("builtins.print"):
                    exec(compile(tail, "colab-quality-gate", "exec"), namespace)
                self.assertEqual(bool(downloaded), allowed)
            a3 = json.loads((ROOT / "notebooks/exp-a3-source-role.ipynb").read_text(encoding="utf-8"))
            score = next("".join(c["source"]) for c in a3["cells"] if c.get("id") == "score")
            a3_tail = score[score.index("baseline_f1 ="):]
            for tps in ((0, 0, 0), (1, 0, 1), (1, 1, 1)):
                for item, tp in zip(("v10", "v18", "v20"), tps):
                    namespace["metrics"]["items"][item].update(tp=tp, fp=10)
                downloaded.clear()
                with patch.dict(sys.modules, {"google.colab": colab}), patch("builtins.print"):
                    exec(compile(a3_tail, "a3-tp-gate", "exec"), namespace)
                check = json.loads((results / "a3-target-check.json").read_text(encoding="utf-8"))
                self.assertEqual(check["all_target_tp_positive"], all(tps))
                self.assertEqual(bool(downloaded), all(tps))
                self.assertFalse(check["performance_accepted"])
            report["reproduction"]["settings"]["max_tokens"] = 4096
            write()
            with self.assertRaisesRegex(RuntimeError, "기본 추론 설정"):
                namespace["check_live"]("dev", 200)
            report["reproduction"]["settings"]["max_tokens"] = 2048
            report["reproduction"]["packages"]["vllm"] = "wrong"
            write()
            with self.assertRaisesRegex(RuntimeError, "패키지"):
                namespace["check_live"]("dev", 200)
            report["reproduction"]["packages"]["vllm"] = "0.26.0"
            write()
            (work / "cases/dev/script.py").write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "제출 ZIP"):
                namespace["check_live"]("dev", 200)
            downloaded = []
            colab.files.download = downloaded.append
            with patch.dict(sys.modules, {"google.colab": colab}):
                exec(compile(CELLS["collect"], "colab-collect", "exec"), namespace)
            with zipfile.ZipFile(downloaded[0]) as archive:
                self.assertIn("mock/diagnostics.jsonl", archive.namelist())
                self.assertNotIn("submit.zip", archive.namelist())
            with zipfile.ZipFile(bundle, "a") as archive:
                archive.writestr("../escape.txt", "bad")
            with patch.dict(sys.modules, {"google.colab": colab}), self.assertRaisesRegex(ValueError, "파일 목록"):
                exec(compile(CELLS["upload"], "colab-upload", "exec"), namespace)
            self.assertFalse((tmp / "escape.txt").exists())

    def test_diagnostic_run_is_on_by_default_and_refuses_a_silent_no_op(self):
        """기본 셀 그대로 원응답을 보존하고, 실제 옵션/본문이 누락되면 실패한다."""
        self.assertIn("RUN_DIAGNOSTIC = True", CELLS["diagnose"])
        self.assertNotIn("check_live", CELLS["diagnose"])  # 진단 회차는 검증 통과로 세지 않는다.
        source = CELLS["diagnose"]
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results"
            (results / "dev-debug").mkdir(parents=True)
            calls, settings, events = [], {}, []
            def fake_run_case(name, source_path, args=()):
                calls.append((name, list(args)))
                (results / name / "run_report.json").write_text(
                    json.dumps({"mode": "live", "reproduction": {"settings": settings}}), encoding="utf-8")
                (results / name / "diagnostics.jsonl").write_text(
                    "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
            namespace = dict(WORK=Path(tmp), RESULTS=results, json=json, run_case=fake_run_case,
                             write_json=lambda path, value: path.write_text(
                                 json.dumps(value, ensure_ascii=False), encoding="utf-8"))
            settings.update(debug_responses=True, sme_items=["v13"])
            events[:] = [{"event": "response", "response_text": "{}"},
                         {"event": "run_succeeded"}]
            with patch("builtins.print"):
                exec(compile(source, "colab-diagnose", "exec"), namespace)
            self.assertEqual(calls, [("dev-debug", ["--debug-responses"])])
            record = json.loads((results / "diagnostic.json").read_text(encoding="utf-8"))
            self.assertIs(record["colab_pass"], False)
            self.assertEqual(record["responses"], 1)

            settings["debug_responses"] = False  # 플래그가 안 먹은 회차
            with patch("builtins.print"), self.assertRaisesRegex(RuntimeError, "원응답을 켜지"):
                exec(compile(source, "colab-diagnose", "exec"), dict(namespace))
            settings["debug_responses"] = True  # 플래그는 켰는데 본문이 안 남은 회차
            events[:] = [{"event": "response"}]
            with patch("builtins.print"), self.assertRaisesRegex(RuntimeError, "기록되지 않았"):
                exec(compile(source, "colab-diagnose", "exec"), dict(namespace))

    def test_item_diagnosis_calls_the_separate_tool_without_a_token(self):
        """항목 진단은 제출물이 아닌 tools/diagnose_items.py를 부르고 기본으로 꺼져 있다."""
        self.assertIn('DIAGNOSE_ITEMS = ""', CELLS["diagnose"])
        source = CELLS["diagnose"].replace('DIAGNOSE_ITEMS = ""', 'DIAGNOSE_ITEMS = "v16,v18,v20"')
        source = source.replace("RUN_DIAGNOSTIC = True", "RUN_DIAGNOSTIC = False")
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            results = work / "results"
            (results / "diagnose").mkdir(parents=True)
            (results / "diagnose/manifest.json").write_text(
                json.dumps({"stages": {"v16": {"condition_not_met": 3}}}), encoding="utf-8")
            calls = []
            namespace = dict(WORK=work, RESULTS=results, json=json, os=os, Path=Path,
                             PYTHON=sys.executable, MODEL_DIR="/models/revision",
                             SUBMISSION=work / "submission",
                             run_logged=lambda name, command, env=None, cwd=None:
                                 calls.append((name, [str(x) for x in command], env)))
            with patch.dict(os.environ, {"HF_TOKEN": "test-token", "PPS_QUANT": "wrong"}), \
                    patch("builtins.print"):
                exec(compile(source, "colab-diagnose", "exec"), namespace)
            self.assertEqual([name for name, _, _ in calls], ["diagnose"])
            _, command, env = calls[0]
            self.assertTrue(any(Path(part).name == "diagnose_items.py" for part in command), command)
            self.assertEqual(command[command.index("--items") + 1], "v16,v18,v20")
            self.assertEqual(command[command.index("--model-dir") + 1], "/models/revision")
            # 저장소 루트 사본이 아니라 실제로 푼 제출 코드를 가리켜야 한다.
            self.assertEqual(Path(command[command.index("--script") + 1]),
                             work / "submission/script.py")
            self.assertNotIn("HF_TOKEN", env)
            self.assertNotIn("PPS_QUANT", env)
            self.assertEqual(env["HF_HUB_OFFLINE"], "1")

    def test_notebook_preserves_subprocess_failure_log_and_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            namespace = dict(WORK=Path(tmp), RESULTS=Path(tmp), json=json, time=time, subprocess=subprocess,
                             os=os, Path=Path, PYTHON=sys.executable)
            exec(notebook_functions(), namespace)
            command = [sys.executable, "-X", "utf8", "-c",
                       "import sys; print('원인 stdout'); print('원인 stderr', file=sys.stderr); sys.exit(7)"]
            with self.assertRaisesRegex(RuntimeError, "exit=7"):
                namespace["run_logged"]("failed", command)
            log = (Path(tmp) / "failed.log").read_text(encoding="utf-8")
            self.assertIn("원인 stdout", log)
            self.assertIn("원인 stderr", log)
            record = (Path(tmp) / "failed-command.json").read_bytes()
            self.assertEqual(json.loads(record)["returncode"], 7)
            with self.assertRaises(ValueError):
                namespace["run_logged"]("failed", command)
            self.assertEqual((Path(tmp) / "failed-command.json").read_bytes(), record)

    def test_venv_children_find_installed_executables(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            builder = venv.EnvBuilder(with_pip=False)
            builder.create(work / "venv")
            context = builder.ensure_directories(work / "venv")
            python = context.env_exec_cmd
            # A real native executable stands in for pip's ninja console executable.
            probe = "colab-path-probe.exe" if os.name == "nt" else "colab-path-probe"
            shutil.copy2(shutil.which("cmd.exe" if os.name == "nt" else "echo"),
                         Path(python).parent / probe)
            namespace = dict(WORK=work, RESULTS=work, PYTHON=python, Path=Path,
                             json=json, time=time, subprocess=subprocess, os=os)
            exec(notebook_functions(), namespace)
            args = [probe, "/c", "echo", "path-ok"] if os.name == "nt" else [probe, "path-ok"]
            code = ("import os, subprocess, sys; "
                    f"subprocess.run({args!r}, check=True); "
                    "assert os.environ['VIRTUAL_ENV'] == sys.prefix")
            custom_env = dict(os.environ, HF_TOKEN="test-only-token")
            original_env = custom_env.copy()
            namespace["run_logged"]("default-env", [python, "-c", code])
            namespace["run_logged"]("explicit-env", [python, "-c", code], env=custom_env)
            self.assertEqual(custom_env, original_env)
            for name in ("default-env", "explicit-env"):
                self.assertIn("path-ok", (work / (name + ".log")).read_text(encoding="utf-8"))
                self.assertNotIn("test-only-token", (work / (name + "-command.json")).read_text())


if __name__ == "__main__":
    unittest.main()
