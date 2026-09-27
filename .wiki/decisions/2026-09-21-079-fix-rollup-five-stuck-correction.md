---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Correct \"The five have one common cause\" in ROLLUP §4"
pr: 79
merged: 2026-09-21
branch: "fix/rollup-five-stuck-correction"
---

# docs: Correct "The five have one common cause" in ROLLUP §4

What. #78 must be merged first. This document points to three files in astra using relative paths.

Why. The §4 of `ROLLUP.md`, which entered main via `#75`, contains an incorrect claim from the main session. > The five unchanged ones (v10·v13·v18·v20·v24) converge to a single cause. The main session and astra independently analyzed the same question and both disproved it. Since there are only 0~3 pairwise intersections out of 65 unioned incorrect answer notices, the explanation that one failure in the same few notices creates five scores does not hold. If left as is, the next session will read it as fact. The main session's board has been discarded (PR #77 closed, branch deleted). This topic is owned by the three documents in #78. ``` reports/team-c/a5-label-definition/five-stuck-analysis. …

Source. PR #79 · `fix/rollup-five-stuck-correction`
