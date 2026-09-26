---
scope: project
severity: contract
triggers: ["절대 경로", "개인 경로", "run_report", "diagnostics", "script.py", "record_path", "check_live"]
domain: 'artifacts'
title: "fix: Remove absolute paths from execution logs of submitted code"
branch: "fix/portable-paths-in-script"
---

# fix: Remove absolute paths from execution logs of submitted code

What. Close the gap left by [015](2026-09-17-015-fix-portable-paths-in-records.md). Insert `record_path()` into `script.py` to change the paths written to `run_report.json`, `diagnostics.jsonl`, and console logs to relative paths based on the submission folder. If it is outside, it is `<외부>/<파일명>`. Actual I/O and hash calculations use the original values as they are. For Colab notebook `check_live`, one line was changed to compare the recorded `model_dir` with the fixed revision name.

Why. Following user confirmation, the risk of submission errors was investigated first, and it was only confirmed that there is no place where the recorded path string is functionally read, but it has not been proven by actual GPU/server execution. I checked all consumers. `tools/package.py` and `tests/test_baseline.py` only read `mode`, `model_success_count`, and `model`, `tools/langfuse_tail.py` only passes `settings` for display purposes, and `asset_sha256` calculates with a separate `assets` dictionary, so it is irrelevant to this change. The only coupling was the `settings["model_dir"] != MODEL_DIR` comparison in notebook `check_live`, which was caught by the test. Since the absolute path prefix was not evidence of integrity, it is changed to whether the snapshot folder name is a fixed revision. `record_path()` is made not to raise exceptions for any input so that logs do not break inference.

Verification: I reproduced the `C:/` being caught on both `run_report.json` and `diagnostics.jsonl` by mock-executing the pre-fix `script.py` as is, and confirmed 0 regression tests after the fix. I added the log path format and pattern check to `tests/test_baseline.py::test_mock_cli_and_invalid_inputs`. 28 cases OK, Ruff passed. The submission ZIP SHA-256 changes as well because the code has changed.
**It has not yet been verified with actual GPU/Colab runs and server submissions.**

Source. `script.py` `record_path()` · `notebooks/colab-baseline.ipynb` `check_live` ·
`tests/test_baseline.py`
