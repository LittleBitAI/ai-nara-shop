---
scope: project
severity: contract
triggers: []
domain: ''
title: "fix: Revert full prompt regression and separate judgment for 3 items"
pr: 5
merged: 2026-09-17
branch: "fix/codex-isolate-sme-judgments"
---

# fix: Revert full prompt regression and separate judgment for 3 items

What. The dev F1 of the full prompt statute injection candidate dropped from 0.2208 to 0.1847, so the base 24-item prompt is restored. In the same model, only v10·v11·v13 are judged separately, and the remaining 21 items and evidence are preserved. The existing response split recovery is maintained.

Why. Score the base/final CSV in the same execution. Colab confirms the match between the two-stage success/non-target cells, and automatically downloads the submission ZIP only when the base F1 of the same execution is higher than the past baseline. Verification: 21 local checks, dev 200-case base message perfectly matches 1c64604, fixed tokenizer separate prompt budget, decompression mock·Ruff·nbformat·UTF-8/LF·diff checks passed. The new candidate's actual GPU score/time and server success are unverified. Independent review is omitted per user instruction.

Source. PR #5 · `fix/codex-isolate-sme-judgments`
