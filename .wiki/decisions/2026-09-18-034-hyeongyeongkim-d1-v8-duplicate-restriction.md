---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: recover the first true positives for v8, v7, v4 and cut v3 false positives"
pr: 34
merged: 2026-09-18
branch: "HyeongyeongKim/d1-v8-duplicate-restriction"
---

# feat: recover the first true positives for v8, v7, v4 and cut v3 false positives

What. This is the result of running D0~D6 for the D person in charge to the end. The 4 items with restricted participation qualifications are treated as post-processing candidates.

Why. | Item | Ticket | Pre TP/FP/FN | Post TP/FP/FN | F1 | Contribution | | --- | --- | --- | --- | --- | --- | | v8 | D1 | 0 / 0 / 6 | 6 / 0 / 0 | 0 → 1.000000 | +0.041667 | | v7 | D2 | 0 / 0 / 7 | 7 / 0 / 0 | 0 → 1.000000 | +0.041667 | | v4 | D3 | 0 / 2 / 6 | 6 / 2 / 0 | 0 → 0.857143 | +0.035714 | | v3 | D6 | 8 / 10 / 0 | 8 / 6 / 0 | 0.615385 → 0.727273 | +0.004662 | | Remaining 20 items | — | No change | No change | — | 0 | Macro F1 0. …

Source. PR #34 · `HyeongyeongKim/d1-v8-duplicate-restriction`
