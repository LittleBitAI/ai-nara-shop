---
scope: project
severity: contract
triggers: ["런처", "게이트", "postgres", "마이그레이션", "ci"]
domain: infra
title: "run: A4 gate server result — dev gain changed sign (0.50578, rejected)"
pr: 86
merged: 2026-09-21
branch: "docs/a4-server-result"
---

# run: A4 gate server result — dev gain changed sign (0.50578, rejected)

What. Record the server results of `3a30167` submitted on 2026-09-21 in the ledger and documentation. There are no code changes. Server 0.5057795952 / 6,300 seconds (105 minutes). Compared to the previous `18f07e5` of 0.5084137874, it decreased by −0.0026341922 for the first time. | | dev replay | server | | --- | ---: | ---: | | `18f07e5` | 0.593846165415 | 0.5084137874 | | `3a30167` | 0. …

Why. The A4 coverage gate did not provide a gain on the server. It is rejected. Since it is not included in the operation `script.py` of `main`, there is nothing to revert, and the server high remains at 0.5084137874 (`18f07e5`). The adopted version is left in `feat/adopt-a4-scope-gate` (`3a30167`) and is not merged. In this comparison, the prompt, schema, and number of calls are all the same, and only the post-processing is different, so the dev side is **same original response replay↔replay**. Even though +0.017878 was a pure code effect with no churn, it did not go to the server. The v23 unlabeled utterance ratio 0.05 warning, noted in advance in A4 report §5, was confirmed by actual measurement. However, even if the entire dev contribution of 0.0089 of v23 is lost, the loss is 0. …

Source. PR #86 · `docs/a4-server-result`
