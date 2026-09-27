---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: Determine v20 as two facts of the announcement, not a model (Adopted)"
pr: 111
merged: 2026-09-23
branch: "feat/c-v20-sw-clause"
---

# feat: Determine v20 as two facts of the announcement, not a model (Adopted)

What. These are the v20 post-processing candidates and their evidence. Adopted judgment on 2026-09-23. `script.py` will not be touched — the integrated submission collecting adopted candidates will carry over this candidate. Wait without merging until the submission integration. | File | Content | | --- | --- | | `experiments/v20_sw_clause_candidate. …

Why. v20 is 1/4/4 (F1 0.200) at HEAD. All 8 misjudgments are misreadings of the announcement — RFP elimination gate hold 3, SW business classification omission 1, failure to cite Article 48 participation restriction specified in the announcement 2 (all 200 are null), SW over-classification 2. Legal injection (#82·A8) could not touch any of these eight. | Measurement | Result | | --- | --- | | dev reproduction (`colab-1789902969401579900/dev-debug`) | v20 1/4/4 → 5/2/0, Macro 0.618427 → 0.644816 (+0.026389), all 10 changed cells are v20, 0 outside target | | Unlabeled ratio (20,000 cases) | Candidate 1 ratio 2.28% vs dev 3.50% → 0. …

Source. PR #111 · `feat/c-v20-sw-clause`
