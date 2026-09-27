---
scope: project
severity: preference
triggers: []
domain: ''
title: "A5: Implementation of v18 scope review and results of two rounds — Not adopted"
pr: 80
merged: 2026-09-21
branch: "feat/a5-v18-scope-review"
---

# A5: Implementation of v18 scope review and results of two rounds — Not adopted

What. We implemented a candidate that consumes the scope_review extracted separately in one company_size call only for v18, and registered the results of two actual GPU rounds. The candidate is not adopted. As of 2026-09-21, it is merged to preserve the experimental code, result records, and ledger modifications with user approval. The production `script.py` remains unchanged. …

Why. The global replacement of the H3 storage scope increased v10 FP while recovering v18 TP. This time, we tested the hypothesis of separating this by consuming a separate scope of the same call only for v18. In reality, scope/review were the same in 199 cases, and 1 case was held as competitive→unknown, so no new TP was generated. The macro difference includes existing field changes and inference fluctuations, not review consumption.

Source. PR #80 · `feat/a5-v18-scope-review`
