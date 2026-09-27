---
scope: project
severity: preference
triggers: []
domain: ''
title: "perf: recheck only baseline-positive v13 notices"
pr: 10
merged: 2026-09-17
branch: "perf/t1-selective-v13"
---

# perf: recheck only baseline-positive v13 notices

What. The additional analysis of all v10, v11, and v13 cases took 330.8 seconds in the latest dev run, but did not change a single v10 or v11 judgment. Now, only baseline v13 positive notices recheck v13, reducing the generation of irrelevant instructions, direct production clauses, and duplicate citations.

Why. It preserves the baseline 24-item inference/failure recovery and the other 23 items. Additional analysis failures maintain the verified baseline judgment of the same notice. Colab compares the counts of selected/skipped/succeeded/failed cases with the actual number of selections in the baseline CSV. Verification: 27 local tests, additional checks for non-contiguous failure indices, Ruff, and 10 mock ZIP extractions with 49 columns passed. In the latest records, additional call targets decreased from 200 to 107, additional input tokens for the same local tokenizer decreased from 2,030,736 to 965,553, and the saved response recombination matches the existing final CSV. Actual GPU time, scores, and server success for the new prompt are unverified. Detailed evidence is recorded in reports/t1-baseline/selective-v13.md. Per user instruction, a separate independent review is omitted. …

Source. PR #10 · `perf/t1-selective-v13`
