---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: Private contract fact path dev tuning (v9·v10·v13·v18) — stack end dev 0.7661"
pr: 137
merged: 2026-09-25
branch: "feat/b-facts-devfit"
---

# feat: adjust private contract fact path for dev (v9·v10·v13·v18) — stack end dev 0.7661

What. If it is `postprocess()` at the end and `계약방법 == 수의계약`, set v9·v10·v13·v18 to 0 (`NO_BID_ZERO_ITEMS`). Refixing: `DELIBERATE_MOVES`·`_H2`·`_A7`, `b5-port-replay`, three expected count locations for v10/v13/v18, D hash. The v2 rounding rule was once included but removed (below).

Why. An experiment to boost underfitting (dev F1 < 0.7) items at the risk of overfitting (user decision). | Item | Before (TP, FP, FN) | After | | --- | --- | --- | | v9 | 5, 7, 1 | 4, 3, 2 | | v10 | 4, 8, 3 | 4, 6, 3 | | v13 | 3, 7, 3 | 3, 2, 3 | | v18 | 2, 4, 5 | 2, 1, 5 | dev replay (`colab-1790250265636150570`) this rule +0.0155. Stack end rebased onto main (#133 v23 axis) 0.766113 — v23 1/0/4 → 5/0/0 is +0.0278. Rejected: catalogue check range (−0.0287 / band only −0.0061), v11 limit observation (−0.0071). …

Source. PR #137 · `feat/b-facts-devfit`
