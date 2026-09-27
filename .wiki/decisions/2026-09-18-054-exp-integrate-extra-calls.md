---
scope: project
severity: preference
triggers: []
domain: ''
title: "exp: Merge three additional call experiments into one main and toggle them with constants"
pr: 54
merged: 2026-09-18
branch: "exp/integrate-extra-calls"
---

# exp: Merge three additional call experiments into one main and toggle them with constants

What. Reduce 5 branches to 1. If the experiment sets (`exp/n1-absence-split`·`exp/n2-amount-band`·`exp/n3-competitive-product`) remain separate, we have to decide which branch to point to for each iteration, and we cannot use them together.

Why. Since all three are independent steps that only add after calling 24 joint items, they can coexist in one file. Each is toggled by a top-level item list — if the list is empty, that step does not run at all. ```python SPLIT_ITEMS = ["v16", "v18"] # N1 — 켜짐 BAND_ITEMS = [] # N2 — 회차 미실행, 꺼짐 PRODUCT_ITEMS = [] # N3 — 시간이 막아 꺼짐 ``` Each iteration contains its own `baseline_submission.csv`. Since it is the same model output, churn does not mix. We do not use absolute Macro comparisons between iterations — the same code produced dev 0.2182 three times and 0.2208 once. …

Source. PR #54 · `exp/integrate-extra-calls`
