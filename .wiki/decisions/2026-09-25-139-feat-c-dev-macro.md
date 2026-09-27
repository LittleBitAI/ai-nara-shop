---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: Increase dev Macro at the risk of overfitting — Merge C candidate set +0.023402577814"
pr: 139
merged: 2026-09-25
branch: "feat/c-dev-macro"
---

# feat: Increase dev Macro at the risk of overfitting — Merge C candidate set +0.023402577814

What. The C part policy changed on 2026-09-25 — Candidates are no longer held back just because the unlabeled ratio is "undecided" or "unmeasurable". The ratio is still measured and recorded but is not used as a reason for rejection. Two previously held-back candidates were re-evaluated based on current criteria, and the remaining dev errors were addressed in order of Macro contribution, merging the three that passed with fixed ordering. dev Macro 0.685506108460 → 0.708908686274 (+0. …

Why. ### Two held-back candidates (Task 1) `c5_v11_absence_signal` — +0.007843, all 7 cells `0→1`. `c_v13_merge` — 0 cells. The application condition is still true for 117 cases, but there are 0 overlaps with the previous stage's positive cases. `PPS-DEV-03`, which was the only one that changed in the past, already had its FP closed by SME re-verification in this round, and the company scope was also flipped from `general` to `competitive`. The rule is not wrong, but there is no target in this output — the same rule closes 6 cases in the 5,500 unlabeled cases. It was left with the reason instead of being discarded. ### Remaining dev errors (Task 2) — In the order determined by policy | Target | Result | | --- | --- | | v18 FN 6 | Passed. …

Source. PR #139 · `feat/c-dev-macro`
