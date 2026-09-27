---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: D9 — Turn on and measure four rules for determining v6 as `단위=기초` tokens separately"
pr: 114
merged: 2026-09-23
branch: "feat/d9-v6-basic-region"
---

# feat: D9 — Turn on and measure four rules for determining v6 as `단위=기초` tokens separately

What. Task [docs/tasks/d-v6-basic-region.md](../blob/feat/d9-v6-basic-region/docs/tasks/d-v6-basic-region.md) · Report [reports/team-d/d9-v6/README.md](../blob/feat/d9-v6-basic-region/reports/team-d/d9-v6/README.md) · Condition table and 20 samples [l2-conditions.md](.. …

Why. Four rules were turned on and measured separately. Version selection and adoption are handled by A, and `script.py` reflection is handled by B. Do not merge. `script.py` was not touched. The default is to have nothing turned on, so if not turned on, this section does not touch v6 and the previous v8·v7·v4·v3 reproduction is reproduced as is. | Reproduction | Macro | Difference | v6 TP/FP/FN | Changed cell | | --- | ---: | ---: | --- | --- | | 0 rules | 0.618427228373 | +0.000000000000 | 3/0/3 | None | | U | 0.628528238474 | +0.010101010101 | 5/0/1 | v6 2 · e6 2 | | L1 | 0.618427228373 | +0. …

Source. PR #114 · `feat/d9-v6-basic-region`
