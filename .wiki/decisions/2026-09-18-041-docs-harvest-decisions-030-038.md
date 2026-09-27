---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Move 8 decision records that were only in the worktree to main"
pr: 41
merged: 2026-09-18
branch: "docs/harvest-decisions-030-038"
---

# docs: Move 8 decision records that were only in the worktree to main

What. Add 8 records (030·031·033·034·035·036·037·038) dated 2026-09-18 to `.wiki/decisions/`. Only the documentation changes. `script.py`·`tools/`·`experiments/` are not touched.

Why. 40 PRs were merged, but there were only 3 decision records for 2026-09-18 in main. The wiki hook created records for the Stop event within the Orca worktree (`anhinga`·`elkhorn`·`squirrelfish`), and those worktrees remained without commits, so they did not reach main. They were in a location that would disappear upon worktree cleanup.

Source. PR #41 · `docs/harvest-decisions-030-038`
