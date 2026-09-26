---
scope: project
severity: contract
triggers: ["런처", "게이트", "postgres", "마이그레이션", "ci"]
domain: infra
title: "C: B1 cleanup — 33 out of 34 cells are outside the gate, and row condition comparison cannot distinguish between range and TP"
pr: 105
merged: 2026-09-23
branch: "feat/c-b1-aftermath"
---

# C: B1 cleanup — 33 out of 34 cells are outside the gate, and row condition comparison cannot distinguish between range and TP

What. Close the 4 unconfirmed items left behind when the B1 round (`colab-1790141677344456786`) closed as rejected using the CPU, and determine if the next design is possible. Did not run a new round — 0 model calls · 0 seconds of GPU. No changes to production code — `git diff --stat -- script.py tools/ notebooks/` empty output.

Why. | | | | --- | --- | | 1 | 33 out of 34 cells are unrelated to the `competitive_row` gate. The gate was triggered in only 7 cases, and the only overlap among the 29 cases with changed cells is `126` | | 2 | The next direction is also blocked. Range and TP point to the same catalog row, and all four axes verifiable by machine cannot distinguish between the two | Initially, I used the archived round CSV as a reference, resulting in 75 cells and 63 outside the target. `docs/workflow.md` This is a landmine blocked by W5 — "If you use the `submission.csv` of the archived round as a reference, the effects of the post-processing merged afterward are mixed in." However, the current HEAD playback is also not the reference. After the judgment (`57e6134`), the v3~v6 gates of the D part are merged, `script. …

Source. PR #105 · `feat/c-b1-aftermath`
