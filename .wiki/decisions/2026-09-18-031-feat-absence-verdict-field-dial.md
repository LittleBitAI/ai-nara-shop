---
scope: project
severity: contract
triggers: []
domain: ''
title: "feat: show the absence recall swings 4x with how the verdict is asked"
pr: 31
merged: 2026-09-18
branch: "feat/absence-verdict-field-dial"
---

# feat: show the absence recall swings 4x with how the verdict is asked

What. Merge the verdict fields of the diagnostic tool into one and register the first GPU round. The misalignment disappeared, but the absence recall dropped from 13/18 to 3/18. Rewrite `reports/team-score-audit/absence-detection.md` as a two-round comparison, and increase churn observations to twelve pairs using the fifth measurement of the same `script.py`.

Why. ### The previous round's "v16 6/6" was not the model's actual performance. It was the same model, same announcement, and same item, but the way the verdict was asked was changed. | | Loose — separate `판정` field (`…172468461`) | Conservative — remove field + instruction for conservatism (`…726180378`) | | --- | --- | --- | | v16 (support 6) | 6 / 139 / 0 · F1 0.079 | 1 / 29 / 5 · F1 0.056 | | v18 (support 7) | 4 / 109 / 3 · F1 0.067 | 2 / 34 / 5 · F1 0.093 | | v20 (support 5) | 3 / 109 / 2 · F1 0.051 | 0 / 0 / 5 · F1 0. …

Source. PR #31 · `feat/absence-verdict-field-dial`
