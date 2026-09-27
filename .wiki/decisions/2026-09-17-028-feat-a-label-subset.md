---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: cover every item with 50 notices instead of paying 33 hours for 200"
pr: 28
merged: 2026-09-17
branch: "feat/a-label-subset"
---

# feat: cover every item with 50 notices instead of paying 33 hours for 200

What. `export --cover N --negatives M --truth <csv>` — Select only notices that cover N positive cases for each item. This is a greedy selection, and ties are broken by ID in alphabetical order so that the same input produces the same list (R15). Write the correct answer only for the selection and do not include it in the bundle. Leave the selection method, correct answer hash, and under-threshold items in the manifest. `collect --truth-out` — A subset CSV of correct answers containing only IDs with labels. `tools/score.py` remains untouched. …

Why. The first actual labeling took 303 seconds per notice. 200 notices × 2 models = 33.7 hours. Out of 200 dev notices, only 88 notices have at least one positive case, and 112 notices have 0 for all 24 items. Macro F1 is a positive class metric, so those 112 notices only provide false positive information. | Selection | Number of notices | 2 models | | --- | ---: | ---: | | Positive ≥1 per item | 11 notices | 1.9h | | Positive ≥3 per item + 15 zero-positive | 50 notices | 8.4h | | Total | 200 notices | 33.7h | The 15 zero-positive notices reduce bias in false positive measurement. If only notices with positive cases are used, a labeler who answers "all 1s" looks like they are doing well. The F1 of this subset is not on the same axis as the dev 0.2208 of `654c556` …

Source. PR #28 · `feat/a-label-subset`
