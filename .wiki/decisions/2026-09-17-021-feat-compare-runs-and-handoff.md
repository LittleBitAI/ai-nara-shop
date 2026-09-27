---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: give the team a run comparison tool and refresh the stale handoff"
pr: 21
merged: 2026-09-17
branch: "feat/compare-runs-and-handoff"
---

# feat: give the team a run comparison tool and refresh the stale handoff

What. `docs/tasks/team-handoff.md` 359 lines, base commit `693c695`. What I checked today had 0 lines reflected. If you clean the board and don't tell anyone, it's the same as not cleaning it.

Why. Established §0 and placed four actual measurements at the very front: | What was checked | Value | | --- | --- | | First server scoring | `654c556` leaderboard 0.2197036943 (dev 0.2207877113) | | 14% time margin | 6,192 seconds / 7,200 seconds = 86.0%, margin 1,008 seconds, 1 L40S | | Fluctuation between rounds | Macro F1 0.0025 in two rounds under the same conditions, v cell 25/4,800 | | `36b6cc1` actual measurement | dev 0.2182553450, additional inference 330.8→110.7 seconds, not submitted | §1 (score), §10 (ZIP delivery → `git pull`), §12 (inspection command + 3 steps after round), and common instructions were also fixed. …

Source. PR #21 · `feat/compare-runs-and-handoff`
