---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: C5 v11 candidate is reproduced in two new model outputs — (a), (b), and (d) confirmed without iterations"
pr: 136
merged: 2026-09-25
branch: "docs/c5-v11-new-outputs"
---

# docs: C5 v11 candidate is reproduced in two new model outputs — (a), (b), and (d) confirmed without iterations

What. I confirmed the premise of the C5 v11 candidate in two new model outputs without running GPU iterations. Only the documents and tests change — `script.py` unchanged · 0 model calls · 0 GPU seconds. While pulling the repository, I saw that two iterations of D left `dev-debug` original responses. Since these are new outputs rather than fixed original responses, I was able to answer (a), (b), and (d) which `RUN-REQUEST.md` had passed to a new iteration. …

Why. The question (a) of `RUN-REQUEST.md` was the most uncertain — this candidate is subject to the model's absence observation (`direct_production_quote == null`), so there was no guarantee that the 6 cases of the fixed original response would be the same in the new output. They came out as 6 and 7 in the two sets. It is within the baseline E range (3~12) and (a) was not negated. Also, since `changed_cells_off_focus` is 0 across different output sets, it was confirmed that the candidate not touching outside of `v11` is not a coincidence of one set. This does not replace iterations. I wrote the three in the main text. 1. (c) churn could not be measured — the code of the two iterations is different (`427b971` vs `f6fd6fb`). Churn is only measured with two iterations of the same code. 2. …

Source. PR #136 · `docs/c5-v11-new-outputs`
