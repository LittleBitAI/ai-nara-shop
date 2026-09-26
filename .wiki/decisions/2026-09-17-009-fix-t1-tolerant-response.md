---
scope: project
severity: contract
triggers: []
domain: ''
title: "fix: accept equivalent binary judgments and ignore extra fields"
pr: 9
merged: 2026-09-17
branch: "fix/t1-tolerant-response"
---

# fix: accept equivalent binary judgments and ignore extra fields

What. Even if the model returned binary values with the same meaning or additional explanation fields, the existing check could reject the response, leading to retries or total termination. Clear bool/number/string binary values are normalized to integers 0/1, and only additional fields are discarded.

Why. If essential judgments or facts are missing or the values are ambiguous, the existing split recovery is maintained. Announcements without normal responses are not filled with 0. Prompts, input budgets, score conditions, and CSV contract are maintained. Verification: In the 16 combinations of basic/additional steps for chunk 62, it failed before the fix and passed without unnecessary re-calls after the fix. baseline 17 + package 5 + score 4 checks, Ruff/diff/UTF-8/LF, and ZIP mock verification passed. Confirmed identity of 200 dev prompt and normal JSON parsing results. The team member's successful submission is identical to the provided baseline, and the actual response type that caused the initial server error is unconfirmed. The actual GPU/server success and score improvement of the new candidate are unverified. Independent review is omitted per user instruction.

Source. PR #9 · `fix/t1-tolerant-response`
