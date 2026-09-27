---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: A5 diagnosis and H2 unlabeled GPU round preparation"
pr: 71
merged: 2026-09-21
branch: "LittleBitAI/a5-label-wall"
---

# feat: A5 diagnosis and H2 unlabeled GPU round preparation

What. The latest addition is the A5 H3 specified condition observation pilot. `colab-a5-scope.ipynb` executes `173533093617e340f4d4d5858d39766726cf0488` fixedly. In the same company_size call, it first outputs the specified code, condition citation, and condition status, and maintains the existing H2 consumer. 200 control/candidate dev cases and 5 diagnosis cases each are repeated in separate runtimes with the order swapped. …

Why. We are changing the plan that adopted full collection of 20,000 cases as an essential prerequisite for judgment. Rather than executing the remaining 18 rounds consecutively, we first appreciate the original text validity and input distribution of the 83 predicate passes secured (9 dev + 74 unlabeled). We do not set 2,000 cases as the new universal pass line or declare a multiplier of 1.033 as the generalized pass. `complete=false` is maintained with the precise meaning of incomplete full collection. The Wilson/delta method arithmetic in the brief has been reproduced. However, the model estimating the dev population ratio is different from the empirical ratio of the fixed dev/finite unlabeled total. The interpretation that an RSE of 57.6% necessarily remains even in full collection does not hold. This approximation formula does not guarantee the representativeness of sequential sampling, nor the effect of selecting candidates from clusters and dev. …

Source. PR #71 · `LittleBitAI/a5-label-wall`
