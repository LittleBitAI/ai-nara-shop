---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat(v21): v21 citations without equity ratios cannot establish v21 (B10)"
pr: 130
merged: 2026-09-25
branch: "feat/b-v21-quote-share"
---

# feat(v21): v21 citations without equity ratios cannot establish v21 (B10)

What. `script.py` `evidence_refutes()` branches of v21 — v21 generation that does not cite equity ratios below the legal minimum is lowered. `V21_JOINT_BARRED` deletion. `tools/label_bundle.py` — Single item/article extraction mode (`--items`·`--law-excerpt`) and fact extraction mode (`--question`·`--keys`). Record usage of `--output-format json` per call. …

Why. 84 cases (1.4%) of v21 generation in the 6,000-case unlabeled round are all citations without equity ratios (type `공동수급이 허용되지 않습니다`). The operation-disallowed regex caught 0 out of those 84 cases. The 5 dev reconnaissance cases all cite equity ratios below the minimum. The labeler quota issue was also fixed. The previous labeler had about 104k cache writes, 421k reads, and 8.9 turns per announcement (181 transcripts). By turning off the tool and asking only for facts, it is about 20k and 1 turn.

Source. PR #130 · `feat/b-v21-quote-share`
