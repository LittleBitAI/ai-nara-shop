---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: Integrate four eligibility rules into the production code (B5)"
pr: 42
merged: 2026-09-18
branch: "feat/b5-integrate-qualification-rules"
---

# feat: Integrate four eligibility rules into the production code (B5)

What. Move the v8, v7, v4 rounding up and v3 rounding down, which were in D's `experiments/qualification_candidate.py`, to step ⑤ of `script.py` `postprocess` (⑤ runs before ①~④). The candidate module was left as is, and only the rule body was copied byte-for-byte. There were only two name collisions — `ITEMS` → `QUALIFICATION_ITEMS`, `apply` → `apply_qualification_rules`. The submission ZIP is `script. …

Why. (There is no reason clause in the PR body. The evidence for this decision was not recorded)

Source. PR #42 · `feat/b5-integrate-qualification-rules`
