---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: lower v9/v19/v21/v24 positives whose own evidence refutes the item"
pr: 30
merged: 2026-09-18
branch: "feat/b-evidence-rules"
---

# feat: lower v9/v19/v21/v24 positives whose own evidence refutes the item

What. I inserted the step 4 `evidence_refutes()` into `script.py` `postprocess`. If the evidence cited by the model contradicts the violation condition of that item itself, it sets the positive to 0. - v19: If the evidence contains contract time, contract conclusion, or successful bidder determination and lacks `입찰`·`투찰` - v24: If the amount, regional restriction, or (contract method, amount range) in the evidence matches all meta-fields with the same meaning - v21: If all equity ratios are 10% or higher, or if it is a phrase disallowing joint contracts without numerical values - v …

Why. The FP of the 4 items in charge (v9·v19·v21·v24) accounted for 114 cases (as of this round), which is the majority of total false positives. Measured by replaying the stored original response (`colab-1789655036303880754/dev-debug`). Since it uses the same model output for candidates and criteria, there is no churn between rounds. | Item | TP | FP | F1 | | --- | --- | --- | --- | | v19 | 6→6 | 21→16 | 0.3636→0.4286 | | v24 | 4→4 | 43→33 | 0.1455→0.1778 | | v21 | 4→4 | 34→9 | 0.1818→0.4211 | | v9 | 5→5 | 16→11 | 0.3704→0.4545 | Changes outside the target are 0 cells. The dev Macro F1 is 0.2182→0.2357. …

Source. PR #30 · `feat/b-evidence-rules`
