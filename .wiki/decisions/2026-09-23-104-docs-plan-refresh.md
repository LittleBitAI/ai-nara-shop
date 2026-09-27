---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Rewrite the active plan as of 9/23"
pr: 104
merged: 2026-09-23
branch: "docs/plan-refresh"
---

# docs: Rewrite the active plan as of 9/23

What. Rewrite `.wiki/plan-active.md` from 555 lines to 140 lines. Current numbers (five server submissions, transition rate, HEAD replay 0.618427) · HEAD 24-item metrics (by person in charge) · Rules confirmed this week · Items included in `main` · Rejected hypotheses · Open PRs #98~#101 · Next tasks by person in charge · Things A will decide · Decisions to protect. `docs/tasks/team-handoff. …

Why. The plan document accumulated daily progress from 9/17~9/22, causing non-current lines to be mixed in — "A8 followed by two GPU rounds" (already rejected), row B containing only "B1~B4 adoption complete", assignment of A1 to astra, etc. As a document injected at the start of a session, old lines became subsequent task instructions. PRs #1~#103, `.wiki/decisions/`, `reports/submissions.json`, `docs/runs.md`, `docs/tasks.md`, and HEAD replay metrics after #96 were re-read to keep only what is currently valid. Daily progress is owned by git history and decision records. Verification: confirmed existence of all relative links and `reads` paths in both documents, `tests/test_baseline. …

Source. PR #104 · `docs/plan-refresh`
