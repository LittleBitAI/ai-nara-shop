---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix(v9): Remove V9_EQUIVALENT — Operations Team S7-14 (B6)"
pr: 122
merged: 2026-09-23
branch: "feat/b-v9-equivalent-gate"
---

# fix(v9): Remove V9_EQUIVALENT — Operations Team S7-14 (B6)

What. In operations `script.py`, we removed the v9 `V9_EQUIVALENT` (if the phrase "equivalent or higher" exists within 300 characters before or after the evidence, it is marked as positive) and `V9_WINDOW`. The `V9_SPEC_FLOOR` that lowers the performance lower bound is kept. Replay fixed set (`tools/replay_run. …

Why. Operations Team S7-14 stated not to determine v9 based solely on the "equivalent or higher" expression. Measured by replay without model calls. | Version | dev Macro | v9 TP/FP/FN | 5,500 unlabeled cases (excluding 6,000 cases of replay rejection u11) | | --- | ---: | --- | --- | | Existing gate | 0.618427 | 4/9/2 | 41 cases lowered (0.75%, 0.37x compared to dev). 29 of them are in the model/manufacturer specified format | | `off`(Adopted) | 0.615376 | 4/13/2 | 41 cases restored | | Only sentences like H2 | 0.616757 | 4/11/2 | 12 cases continue to be lowered, eight are in the "model + equivalent or higher" format | | H1 document unit | 0. …

Source. PR #122 · `feat/b-v9-equivalent-gate`
