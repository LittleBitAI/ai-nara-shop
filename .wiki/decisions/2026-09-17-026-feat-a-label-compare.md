---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: give the label comparison a blind bundle the answers cannot leak into"
pr: 26
merged: 2026-09-17
branch: "feat/a-label-compare"
---

# feat: give the label comparison a blind bundle the answers cannot leak into

What. This is a tool for selecting a generator for labels to be applied to 20,000 unlabeled items. It runs two external LLMs (GPT 6.0 Astra and Claude Opus 5) blindly on 200 dev items with the same prompt and input, comparing them by TP/FP/FN per item against `open/dev_labels.csv`. `tools/label_bundle. …

Why. Answer leakage is the primary risk of this task. If the CLI agent is run within the repository, the blind is automatically broken. `open/dev_labels.csv` holds the 49-column answers, `reports/team-score-audit/cases.jsonl` holds the `"true"`·`"pred"` and evidence span for each case, and the agent, even without malicious intent, searches the repository to find context. Therefore, `export` rejects paths inside the repository, and the bundle only includes the announcement body, item table, and 25 snapshots of provided statutes. I actually stepped on a landmine with encoding. The first 200 executions failed entirely. The child process sent stdout in cp949 and the parent read it in UTF-8, causing Korean keys to arrive corrupted, and the error was `field mismatch ['... …

Source. PR #26 · `feat/a-label-compare`
