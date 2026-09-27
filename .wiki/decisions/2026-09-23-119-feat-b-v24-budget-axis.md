---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: B9 v24 budget axis regeneration candidate — dev v24 5/12/3, unlabeled ratio 0.69, adopted"
pr: 119
merged: 2026-09-23
branch: "feat/b-v24-budget-axis"
---

# feat: B9 v24 budget axis regeneration candidate — dev v24 5/12/3, unlabeled ratio 0.69, adopted

What. `experiments/b_v24_budget_axis_candidate.py` — A regeneration candidate that re-establishes the turned-off v24 budget axis with the meaning of amount. After operation `postprocess()`, if the amount in the body text and the registered value do not match in a notice where v24=0, it is raised to v24=1 · e24=amount phrase in the body text. It is not lowered. Operation `script.py` was not fixed. `tests/test_b_v24_budget_axis_candidate.py` — 20 items. …

Why. v24 undetected `PPS-DEV-29` occurred when the amount in the body text was different from the registered budget but the model output 0, and the current comparison axis only lowered values, so there was no way to restore them. The budget axis had been turned off as P1 for three consecutive rounds. When conditions 1-4 from the task sheet (field-by-field correspondence, rounding equivalence, bidding target scope, unit price contract) were inserted as is, the unlabeled utterance did not decrease much at 559 (ratio 1.86). I read the utterance samples and fixed the parts where the meaning was misinterpreted …

Source. PR #119 · `feat/b-v24-budget-axis`
