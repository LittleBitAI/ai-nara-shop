---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: register a Colab result ZIP pair with one command"
pr: 17
merged: 2026-09-17
branch: "feat/run-registrar"
---

# feat: register a Colab result ZIP pair with one command

What. Register a pair of result ZIPs placed in `artifacts/inbox/` with one command. Eliminate manual unpacking, comparison, and file creation, but ensure that validation failure results in a failure.

Why. It writes ```powershell python -X utf8 tools/register_run.py --inbox artifacts/inbox --code-commit <커밋> ``` `reports/runs/<run-id>/`, `manifest.json`, one row of [index ](docs/runs.md)], and a `.wiki/decisions/<날짜>-NNN-run-<run-id>.md` draft. It does not commit. - Values are copied directly from the files left by the execution and are not recalculated. If it is not in the log, it is a `null`; if there is no score, the index cell is left blank. - For the index, if a row with the same run-id already exists, it fills that row. This is to prevent `미보관` 5 rows from being duplicated. …

Source. PR #17 · `feat/run-registrar`
