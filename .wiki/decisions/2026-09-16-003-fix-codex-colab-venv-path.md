---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: Pass Colab venv execution path and pre-check ninja"
pr: 3
merged: 2026-09-16
branch: "fix/codex-colab-venv-path"
---

# fix: Pass Colab venv execution path and pre-check ninja

What. FlashInfer initialization failed because the venv execution path was not in PATH even though ninja was installed in Colab. The common executor passes PATH and VIRTUAL_ENV to the venv Python command and checks the ninja execution path and version before downloading the model.

Why. Verification: Reproduced the actual child process FileNotFoundError in the existing function, and passed 5 notebook/packaging checks after the fix. Passed Ruff, nbformat, UTF-8/LF, and diff checks. Actual GPU execution after the fix has not been verified. Independent review is omitted per user instruction.

Source. PR #3 · `fix/codex-colab-venv-path`
