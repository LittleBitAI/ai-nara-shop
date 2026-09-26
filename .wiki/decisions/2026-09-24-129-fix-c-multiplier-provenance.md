---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Fix the calculation error in the merged title and lock the 3.11 parsing regression with a test"
pr: 129
merged: 2026-09-24
branch: "fix/c-multiplier-provenance"
---

# docs: Fix the calculation error in the merged title and lock the 3.11 parsing regression with a test

What. Only fix documentation and tests. 0 model calls · 0 GPU seconds · `script.py`·`tools/`·`notebooks/` unchanged.

Why. Regarding the point that §6·§8 should only list one round, `5ff9873` already fixed it right before the merge. Confirmed in `main`. | Section | Current Status | | --- | --- | | §6 Evidence Level | Two rounds in a table — `58af667`(2,000 cases) · `a6eebe1`(4,000 cases) | | §8 Merge Condition | "Satisfied" · Both entered `main` via PR #120(`f0c155d`) | The figures and judgments are also as instructed — there is one agreement among the three methods in v14, the remaining nine are undecided, and the details of how v12·v15·v16, which were "fewer" in the 2,000-case version, were moved to undecided remain in §0-4. I only checked them and did not touch them. The title is "Fourth Base," but in reality, there are three points and two movements. …

Source. PR #129 · `fix/c-multiplier-provenance`
