---
scope: project
severity: preference
triggers: []
domain: ''
title: "A3: Distinguishing Source and Sentence Role for Enterprise Size Extraction and Fixing Colab Execution"
pr: 60
merged: 2026-09-20
branch: "LittleBitAI/a3-zero-items-start"
---

# A3: Distinguishing Source and Sentence Role for Enterprise Size Extraction and Fixing Colab Execution

What. Modify the qualification prompt for enterprise size extraction to distinguish between announcement qualifications, lists of required documents, legal citations/participation exclusions, and 나라장터 meta. Maintain the schema, scope, decision table, post-processing, and number of calls. The A3-specific Colab notebook `notebooks/exp-a3-source-role.ipynb` is fixed to clone inference candidate `b7ac2650eccd0d8a6ae41919260b158987fd30ff`. …

Why. In the original response for the scope round, 4 out of 7 v18 positive cases copied meta.clause content as the evidence for qualification instead of the announcement. In the full dev set, the same phenomenon occurred in 8 cases. This is a candidate to verify the single hypothesis of reading the document source and sentence role first, without exceptions per announcement ID, in the actual model.

Source. PR #60 · `LittleBitAI/a3-zero-items-start`
