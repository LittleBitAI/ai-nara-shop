---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Hypothesis comes before iterations, and independent review comes after effects are shown"
pr: 102
merged: 2026-09-23
branch: "LittleBitAI/refactor-gpu-first-review"
---

# docs: Hypothesis comes before iterations, and independent review comes after effects are shown

What. `docs/workflow.md` Insert the hypothesis workflow order rule into W5 and link it in one line to step 8 of W2. 1. Minimum implementation in the exploration branch → confirm triggering (self-check, not recorded as independent review) 2. Determine TP/FP/FN of target items, regression outside targets, and unlabeled utterance rate through iterations (replay or Colab) 3. No effect → leave only the report and close the branch, 0 rounds of review. Triggering failure or no change in target cells is considered a bug; fix only that case and re-run 4. …

Why. For every hypothesis PR, cases where it was rejected in iterations after about 6 rounds of review were repeated. Reviews check if the code is correct, but cannot see if the hypothesis increases the score. PR #82 had 0 citations in 1,200 calls across two iterations, B1 was rejected with v18 FN 6→6, and in both cases, the model's response determined the result. A8 is still before iterations even after 7 rounds of review and 10 rounds of observation wiring. Colab iterations have no count limit and post-processing candidates take 0.6 seconds to replay, so the most expensive reviews are used only for candidates whose effects have been confirmed. Verification: Document changes only — confirm UTF-8 without BOM·LF. No changes to the code under test. 🤖 Generated with [Claude Code](https://claude.com/claude-code)

Source. PR #102 · `LittleBitAI/refactor-gpu-first-review`
