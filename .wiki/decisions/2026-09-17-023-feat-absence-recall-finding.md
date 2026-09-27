---
scope: project
severity: contract
triggers: []
domain: ''
title: "feat: show the absence items are suppressed by the joint prompt, not unknown to the model"
pr: 23
merged: 2026-09-17
branch: "feat/absence-recall-finding"
---

# feat: show the absence items are suppressed by the joint prompt, not unknown to the model

What. The first actual GPU run of the diagnostic tool (408 seconds). I asked 200 dev cases for v16, v18, and v20 using a separate 3-item schema instead of a 24-item joint prompt.

Why. | Item | Support | Submission Pipeline TP/FP/FN·F1 | Separate Query TP/FP/FN·F1 | | --- | ---: | --- | --- | | v16 | 6 | 0 / 0 / 6 · 0.000 | 6 / 139 / 0 · 0.079 | | v18 | 7 | 0 / 0 / 7 · 0.000 | 4 / 109 / 3 · 0.067 | | v20 | 5 | 0 / 0 / 5 · 0.000 | 3 / 109 / 2 · 0.051 | v16 caught all 6 positive cases. It is an item that had TP=0 for 6 consecutive runs. The nature of the problem changes — it is not that "the model cannot see it," but that "the model sees it, but the output format makes it 0," and the remaining task is not false negative recovery but precision. …

Source. PR #23 · `feat/absence-recall-finding`
