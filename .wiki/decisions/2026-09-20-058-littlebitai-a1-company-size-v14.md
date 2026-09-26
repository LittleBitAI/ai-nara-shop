---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: Establish the first TP for v14, v15, and v16 using the company size decision table (A1)"
pr: 58
merged: 2026-09-20
branch: "LittleBitAI/a1-company-size-v14"
---

# feat: Establish the first TP for v14, v15, and v16 using the company size decision table (A1)

What. The work was done in the astra session of the `merganser` worktree, while registration, measurement, and this text were handled in the main workspace. The ticket is owned by `docs/tasks/a1-company-size.md`, and the design evidence is owned by `reports/team-c/a1-company-size/result.md`. I added the `company_size` step, which extracts the company grade for eligibility once and performs the amount range comparison via code. Three items that were 0 throughout the six rounds have now been established. …

Why. The amount range already matched the correct answer 100%. All 200 dev items have prices, all 8 v14 positive items are above the notified amount, all 6 v15 items are between 100 million and the notified amount, and all 6 v17 items are below 100 million. However, post-processing that only adds an amount gate resulted in a measured +0.0001 — because the model already utters only within the range (39 out of 40 v17 predictions). The horizontal axis was not the problem. The problem was the vertical axis, and that signal was missing from the model output. In the 8 correct v14 positive items, the model did not utter any of v13~v18. Since a missing signal cannot be recovered through post-processing, there was no choice but to change the calling structure. …

Source. PR #58 · `LittleBitAI/a1-company-size-v14`
