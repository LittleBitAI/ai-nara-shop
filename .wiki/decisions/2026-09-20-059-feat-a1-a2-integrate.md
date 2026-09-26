---
scope: project
severity: preference
triggers: []
domain: ''
title: "Merge: Combine A1 company size decision table and A2 competitor product rules"
pr: 59
merged: 2026-09-20
branch: "feat/a1-a2-integrate"
---

# Merge: Combine A1 company size decision table and A2 competitor product rules

What. Merged #57(A2) and #58(A1). **Since the base is `feat/a2-competitive-product`, the diff of this PR only shows the A1 merge portion and the repairs resulting from the integration.** Once #57 is merged, GitHub moves the base to `main`. The combined version was measured on GPU at 0 seconds using the archived original response from the A1 round. This was possible because A2 is purely post-processing. ``` Macro F1 0.434621 → 0.469806 (+0. …

Why. The two candidates look at different items, and since A2 is purely post-processing, there is no interference. There was no reason not to merge them. ### Resolved nine conflicts in favor of A1 Astra and I each fixed the unlabeled rules, `DRIFT_MAX`, reproduction, and notebook, and reached the same conclusion. Since A1 is a structure verified by GPU, taking that side and layering the 94 lines of A2 code on top is the shortest and safest integration. ### However, that choice revived the reproduction defect A1's `replay_run` also only reads `baseline`, `sme`, and `company_size`, ignoring the `split` and `product` original responses. This is the very defect that `0cf061f` of #57 fixed. …

Source. PR #59 · `feat/a1-a2-integrate`
