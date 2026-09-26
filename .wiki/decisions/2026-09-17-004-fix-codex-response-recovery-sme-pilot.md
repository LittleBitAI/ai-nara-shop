---
scope: project
severity: contract
triggers: []
domain: ''
title: "fix: Response split recovery and competing product judgment pilot"
pr: 4
merged: 2026-09-17
branch: "fix/codex-response-recovery-sme-pilot"
---

# fix: Response split recovery and competing product judgment pilot

What. Change the path that repeated failed 24-item responses under the same conditions to a split regeneration of 6 items per corresponding announcement. Verify each group and the final 24 items, and do not process recovery failures as normal CSVs.

Why. Deliver the results of the provision of support for small and medium enterprises act clauses/exceptions and notification item inquiries to v10, v11, and v13 as a performance pilot. Colab records metrics against the provided asset hash and the same dev baseline (F1 0.2208013652894021). Verification: 20 local checks, fixed tokenizer dev 200-case budget check, actual candidate commit clone/packaging, and passing Ruff, nbformat, UTF-8/LF, and diff checks. Actual GPU recovery, F1 improvement, and initial server error resolution for the new candidate are unverified and require a Colab rerun. Independent review is omitted per user instruction.

Source. PR #4 · `fix/codex-response-recovery-sme-pilot`
