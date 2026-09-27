---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: 2 MEDIUM issues from PR #35 review — Combining the evidence text limit for absence and the candidate's script"
pr: 37
merged: 2026-09-18
branch: "fix/c-absence-schema-and-script-binding"
---

# fix: 2 MEDIUM issues from PR #35 review — Combining the evidence text limit for absence and the candidate's script

What. #35 was merged 39 seconds after the review comment, so the 6 pointed-out issues were uploaded to main as is. Among them, only the 2 MEDIUM issues that affect actual execution are fixed here. The 4 LOW issues were not touched.

Why. `reports/team-c/c3-amount-gate/round1-unlock-absence-evidence.diff` round ① diff opens the evidence text for all 24 items to `maxLength: EVIDENCE_MAX`(500), but prompt rule 3 of the same diff actively instructs to cite if an absence item is judged as violation=1. There are 5 absence items. - `MAX_TOKENS` = 2048 - Measured maximum output of the storage round = 1055 tokens (p95 869) → Margin of about 1000 tokens - The diagnose round marked 139 out of 200 cases as v16 positive. A single announcement citing 3~5 absences near the upper limit exceeds 2048. …

Source. PR #37 · `fix/c-absence-schema-and-script-binding`
