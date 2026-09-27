---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Labeler dev 200 cases calibration — Trust 10 · Conditional 3 · Exclude 11"
pr: 127
merged: 2026-09-23
branch: "docs/a-labeler-dev200"
---

# docs: Labeler dev 200 cases calibration — Trust 10 · Conditional 3 · Exclude 11

What. Ran the Opus 5.5 · medium labeler on all 200 dev cases and compared the F1 per item with human ground truth. This table determines which items will use unlabeled labels without human review. 200/200, 0 failures. 181 new cases (4 parallel batches, 1,646~1,804 seconds per batch) + `opus55-recall8`·`opus55-recall11` 19 reused cases (announcement hash 19/19 match) prompt `ba3f89c8…` — Labeler/setting judgment rules same as unlabeled D round are READ before results …

Why. With only 200 dev cases (5~8 positives per item), the standard error of the difference between the two versions is ±0.013, so most changes cannot be judged. To augment with unlabeled labels, the labeler must be trusted, but there are no conditions for human review. Since the dev ground truth was created by humans, it is used to measure the labeler's error rate per item to replace human review. v10·v18·v20 cannot catch a single positive — the labeler does not read the competition-specific definition as intended. v24 false positive 33, v19 false positive 16 — the labeler `1` for this item is mostly wrong. The sensitivity used for deletion cell calibration is not the entire dev positive set, but the model TP cell hit (population same as design audit §7). Added `모델 TP 적중`·`Wilson 하한` columns to the result table. v17 is 5/5, lower bound 0. …

Source. PR #127 · `docs/a-labeler-dev200`
