---
scope: project
severity: contract
triggers: []
domain: ''
title: "feat: Call the actual Gemma 4 via API instead of mock — Accumulate samples without Colab round-trips"
pr: 49
merged: 2026-09-18
branch: "LittleBitAI/google-api-test-fallback"
---

# feat: Call the actual Gemma 4 via API instead of mock — Accumulate samples without Colab round-trips

What. Add `tools/api_run.py`. Import `script.py` as a module and swap only the runner in the same `run()`. If a key exists, it falls back to `gemma-4-26b-a4b-it` of Google AI Studio; if not, it falls back to `MockRunner`. `--mock` enforces mock even if a key exists. `script.py` changes only 4 lines. …

Why. Colab round-trips were the bottleneck for accumulating samples. Every time a prompt line was fixed, I had to open the notebook, upload the ZIP, and wait for the turn, so even a check that only required a few cases consumed one turn. The API runs a few cases locally using the same pipeline. Since some team members do not have keys, I did not discard the mock but made it API-first, falling back to mock if absent. The records must distinguish between the three executions. If the API turn is written as `mock`, it looks like there was no actual call, and if written as `live`, it looks like a normal R4 call was made. Both are wrong. Therefore, the runner holds `mode` and the API turn `model_success_count` is 0. …

Source. PR #49 · `LittleBitAI/google-api-test-fallback`
