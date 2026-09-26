---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: gate absence detection by the amount band the provision sets"
pr: 35
merged: 2026-09-18
branch: "feat/c-absence-detection-gate"
---

# feat: gate absence detection by the amount band the provision sets

What. This is the CPU stage result for C3·C4·C7. The model was not called, and the submission CSV was not created. `script.py` and `tools/` were not touched — both are delivered only as patches. | File | Content | | --- | --- | | `experiments/sme_candidate.py` | v16·v18 amount gate `postprocess` candidates. v20 was not included | | `tests/test_sme_candidate.py` | 18 cases. …

Why. A separate query caught all 6 positive cases for v16, but labeled 139 out of 200 cases as violations. The problem was not false negatives, but precision. The amount boundary was determined by the provided provision, not the distribution. Notification amount = 230 million KRW — Notification 1.a by the Minister of Finance and Economy (Goods and Services, WTO Government Procurement Agreement). Article 2, Subparagraph 3, Item a of the Enforcement Decree of the Act on Contracts to Which the State Is a Party refers to this notification. 100 million KRW boundary — Article 21①10, Item a (less than 100 million KRW → small business/small enterprise)·Item b (100 million KRW or more → small and medium-sized enterprise) of the State Enforcement Decree. Local government also uses the same value — Article 20①12, Item a of the Local Enforcement Decree explicitly refers to the national notification amount, not the Ministry of the Interior and Safety notification. The provisional value of 220 million KRW from the handover had 3 fewer FPs (36 vs 39), but it was not used because there was no evidence in the provided provision. The boundary was not adjusted to match the figures. …

Source. PR #35 · `feat/c-absence-detection-gate`
