---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: The adoption threshold for deletion-type candidates is q < F/2 — from 400 to 60 samples"
pr: 95
merged: 2026-09-22
branch: "docs/unlabeled-design-audit"
---

# docs: The adoption threshold for deletion-type candidates is q < F/2 — from 400 to 60 samples

What. Verify astra's unlabeled redesign response and correct two errors in my report revealed during that process.

Why. `q < F/2` is an exact threshold, not an approximation. v13 numerical binary search result measured threshold `0.176471` = `F/2` `0.176471`, error `6e-16`. - For all four candidates (v3, v4, v13, v17), if 2 true positives are mixed into the deletion set, the sign flips. - Since the threshold per item is 0.21~0.40, astra's uniform `q<0.10` is stricter than necessary. The required sample size decreases from a candidate total of 400 to 60. Opus 5 marks 2 out of 3 v13 public positives as 0 out of 33 dev cases, and v4 marks 3 out of 4 as 0. Since the bias direction makes deletion look correct, that 0 cannot be used for false positive verification. v13 has the lowest threshold and is the item the labeler gets wrong the most, making it the worst leading candidate. …

Source. PR #95 · `docs/unlabeled-design-audit`
