---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: Bundle of dev gain rules held back only due to lack of unlabeled proof — dev 0.6937 → 0.7152"
pr: 135
merged: 2026-09-25
branch: "feat/b-dev-gain-bundle"
---

# feat: Bundle of dev gain rules held back only due to lack of unlabeled proof — dev 0.6937 → 0.7152

What. Built on top of #134 (logprob threshold by item). Moved five dev gain rules that were held back or rejected to production `script.py`. Four were held back due to "inability to prove outside of dev," and v16/v18 were rejected due to data contract conflicts (below). …

Why. Even though the threshold by item (#134) was intentionally tuned to dev, it exceeded 0.819 on the server (0.5315 → 0.5571). User judgment: It has been underfitting until now. Therefore, we are boldly including rules that were held back only due to "lack of proof outside of dev" rather than "evidence of harm" (user decision 2026-09-25).

Source. PR #135 · `feat/b-dev-gain-bundle`
