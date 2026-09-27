---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: logprob threshold by item (S7-12) — server 0.5571175451, new high"
pr: 134
merged: 2026-09-25
branch: "feat/b-logprob-thresholds"
---

# feat: logprob threshold by item (S7-12) — server 0.5571175451, new high

What. `script.py` — The base call receives the top 5 token logprobs and records the P(violation=1) by item in the response log (`item_p1`). `apply_thresholds()` determines the violation status immediately after parsing with `ITEM_THRESHOLDS` — v1 0.8 · v3 0.8 · v4 0.95 · v6 0.6 · v9 0.999 · v22 0.9 · v23 0.6 · v24 0.01. `tools/replay_run. …

Why. User decision (2026-09-24): A bold experiment accepting overfitting for a 0.76 target. It was one of the levers allowed by S7-12 that had never been used. | | Before | After | | --- | ---: | ---: | | dev replay Macro | 0.662425 | 0.693747 (+0.031322) | | server | 0.5314739081 (`9a8f2eb`) | 0.5571175451 (+0.025644) | | server time | 6,386 sec | 6,397 sec | Transition rate 0.819. It was larger than the estimate (+0.0056 · +0.0127) measured from the other half after selecting half of dev.

Source. PR #134 · `feat/b-logprob-thresholds`
