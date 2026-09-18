---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: recover the first true positives for v8, v7, v4 and cut v3 false positives"
pr: 34
merged: 2026-09-18
branch: "HyeongyeongKim/d1-v8-duplicate-restriction"
---

# feat: recover the first true positives for v8, v7, v4 and cut v3 false positives

무엇. D 담당의 D0~D6을 끝까지 돌린 결과다. 참가자격 제한 4항목을 후처리 후보로 다룬다.

왜. | 항목 | 티켓 | 전 TP/FP/FN | 후 TP/FP/FN | F1 | 기여 | | --- | --- | --- | --- | --- | --- | | v8 | D1 | 0 / 0 / 6 | 6 / 0 / 0 | 0 → 1.000000 | +0.041667 | | v7 | D2 | 0 / 0 / 7 | 7 / 0 / 0 | 0 → 1.000000 | +0.041667 | | v4 | D3 | 0 / 2 / 6 | 6 / 2 / 0 | 0 → 0.857143 | +0.035714 | | v3 | D6 | 8 / 10 / 0 | 8 / 6 / 0 | 0.615385 → 0.727273 | +0.004662 | | 나머지 20항목 | — | 변화 없음 | 변화 없음 | — | 0 | Macro F1 0. …

출처. PR #34 · `HyeongyeongKim/d1-v8-duplicate-restriction`
