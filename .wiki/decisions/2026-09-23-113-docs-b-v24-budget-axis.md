---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: B Next Exploration Initiation — Re-establishing the path to raise the v24 budget axis"
pr: 113
merged: 2026-09-23
branch: "docs/b-v24-budget-axis"
---

# docs: B Next Exploration Initiation — Re-establishing the path to raise the v24 budget axis

What. `docs/tasks/b-v24-budget-axis.md` — New initiation document. The new session starts with this one line of path. `docs/tasks.md` — One line in the work queue. `.wiki/plan-active.md` — Changed row B to the results of this round (#108, #109, #110 pending, #112 rejected) and the next task (approval for users holding both A and B).

Why. Among the low F1 items of B (v24 0.333, v9 0.421), the path to raise based on evidence from clauses and management responses is the single v24 budget axis. The unexplored `029` has a base amount in the text of 37,930,000 ↔ registered allocated budget of 39,730,000 (digits swapped), and an estimated price in the text of 34,481,818 ↔ registered 36,118,183, but the model output 0, and the current comparison axis only outputs positives, so it cannot be revived. I first measured that the turned-off `amount_diff()` should not be turned on as is — 1 true positive out of 3 dev utterances (`029`), 605 utterances out of 20,000 unlabeled (3.0%, 2.0 times compared to dev). This is a risk in the opposite direction of the title tag axis (0 unlabeled cases). `script. …

Source. PR #113 · `docs/b-v24-budget-axis`
