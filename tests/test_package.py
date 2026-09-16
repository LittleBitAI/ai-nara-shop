"""제출 ZIP과 Colab 실행 경로를 모델 없이 검증한다."""

import ast
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
                             json=json, time=time)
            exec(notebook_functions(), namespace)
            with patch("builtins.print"):
                exec(compile(CELLS["clone"], "colab-clone", "exec"), namespace)
            source = json.loads((results / "source.json").read_text())
            actual = subprocess.check_output(["git", "rev-parse", "main"], cwd=ROOT, text=True).strip()
            self.assertEqual(source["commit"], actual)
            with zipfile.ZipFile(namespace["BUNDLE_PATH"]) as bundle:
                with zipfile.ZipFile(io.BytesIO(bundle.read("submit.zip"))) as submit:
                    self.assertEqual(submit.read("script.py"), (ROOT / "script.py").read_bytes())

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
                             time=time, subprocess=subprocess, os=os, shutil=shutil, gzip=gzip,
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
            report_path = results / "dev/run_report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            # Synthetic success metadata exercises the gate only, never a live-model result.
            report.update(mode="live", model_success_count=200, model={"id": "test", "expected_revision": "test"})
            report["environment"]["cuda"] = "13.0"
            report["reproduction"].update(python="3.12.13", packages=namespace["EXPECTED_PACKAGES"].copy())
            def write():
                report_path.write_text(json.dumps(report), encoding="utf-8")
            write()
            namespace["check_live"]("dev", 200)
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

    def test_notebook_preserves_subprocess_failure_log_and_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            namespace = dict(WORK=Path(tmp), RESULTS=Path(tmp), json=json, time=time, subprocess=subprocess)
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


if __name__ == "__main__":
    unittest.main()
