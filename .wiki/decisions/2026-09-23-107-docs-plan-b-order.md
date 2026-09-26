---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Change B order to operational integration → v24 → B6 → v19 (A decision)"
pr: 107
merged: 2026-09-23
branch: "docs/plan-b-order"
---

# docs: Change B order to operational integration → v24 → B6 → v19 (A decision)

What. Change the B order of the activation plan based on the A decision on 2026-09-23.

Why. Before: B6 v9 → v24 FP 12 → v19 FP 3 · operational integration - After: operational integration/submission candidate → v24 FP 12 → B6 v9 → v19 FP 3 Reason: B6 is not about scores but about reducing server risk (0.6% of announcements touched by `V9_EQUIVALENT` out of 2,000 unlabeled cases, a gate that was in every submission since 9/18). v24 has the most false positives with a main dev playback of 4/12/4. HEAD has gate #96 which is not submitted to the server. Changed files: `.wiki/plan-active.md` B row, `docs/tasks/b-v9-equivalent-gate.md` priority sentence. No code changes. 🤖 Generated with [Claude Code](https://claude. …

Source. PR #107 · `docs/plan-b-order`
