---
scope: project
severity: preference
triggers: []
domain: ''
title: "run: Register two rounds of A8 — injection could not move v20 even one space"
pr: 90
merged: 2026-09-22
branch: "run/a8-v20-two-episodes"
---

# run: Register two rounds of A8 — injection could not move v20 even one space

What. Both rounds were completed validly, and the A8 hypothesis is rejected/not adopted. The judgment criteria are [two-round execution design](docs/tasks/a8-v20-two-episode-run.md) §3·§6, and the full text is owned by [result report](reports/team-c/a8-v20-annex/results.md).

Why. | Round | Group | TP | FP | FN | Macro F1 | | --- | --- | ---: | ---: | ---: | ---: | | 1 | control | 1 | 4 | 4 | 0.591008188119 | | 1 | a8 | 1 | 4 | 4 | 0.588468081167 | | 2 | a8 | 1 | 4 | 4 | 0.589442740036 | | 2 | control | 1 | 4 | 4 | 0.586932341938 | TP `PPS-DEV-133` · FP `056`·`064`·`068`·`144` · FN `24`·`131`·`132`·`134` — The four groups have the same ID set. `compare_runs. …

Source. PR #90 · `run/a8-v20-two-episodes`
