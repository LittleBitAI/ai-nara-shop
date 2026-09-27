---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: Preserve inference failure diagnostics and validate Colab submission code"
pr: 1
merged: 2026-09-16
branch: "docs/codex-t1-diagnosis"
---

# fix: Preserve inference failure diagnostics and validate Colab submission code

What. Supplements the issue where cause messages and generation information disappeared when server submission was interrupted by a `정상 모델 응답 재시도 실패 (ValueError)`. Even in case of failure, execution settings, asset hashes, announcement locations, termination reasons and token counts for initial/retry attempts, and cause tracebacks are preserved in JSONL.

Why. Colab prepares a fixed-revision model with HF_TOKEN and then executes the code in the actual submission ZIP like a server using `python script.py` and PPS paths. It checks Python, core packages, basic inference settings, and ZIP consistency, and downloads the same submission ZIP after passing sample/dev validation and scoring. Validation: 9 baselines, 3 package/Colab paths, and 4 scores passed. 10 mock samples/200 dev cases, ZIP extraction execution, notebook syntax/nbformat, and Ruff/diff checks passed. Actual Colab GPU execution and server resubmission are not performed, and server success is not guaranteed due to private inputs, GPU/memory, and overall server time differences. Independent review is omitted per user instruction. …

Source. PR #1 · `docs/codex-t1-diagnosis`
