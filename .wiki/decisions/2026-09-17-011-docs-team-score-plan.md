---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Connecting the 4-person score improvement plan and the current plan wiki"
pr: 11
merged: 2026-09-17
branch: "docs/team-score-plan"
---

# docs: Connecting the 4-person score improvement plan and the current plan wiki

What. Based on the current dev Macro F1 0.2208 and 6 execution records, we summarize the 1-week 0.60 challenge plan for the 4-person team. It provides 24 items in charge, 19 tickets, TP recovery criteria for C3(v16/v18)·D1(v8) for the first 48 hours, and Opus delivery instructions. Target scores and actual achievement figures are distinguished, and recovery from existing server failures is protected.

Why. Updated the current plan summary and document entry point of the project wiki. Confirmed that goals, priority tasks, and detailed documents are injected from the current plan, team member tasks, next task questions, and direct execution of SessionStart. Verification: Actual 6 CSV re-scoring matches, 24 items assigned, 19 tickets, 12 original case references cross-checked, 11 files UTF-8/LF, 68 local links, JSON parsing, diff check, wiki sync, and repo_lint passed. Direct injection records are in reports/team-score-audit/wiki-checks.json. This is a document change; new model inference, server submission, and team member PC verification were not performed. Merging without separate review as per user request.

Source. PR #11 · `docs/team-score-plan`
