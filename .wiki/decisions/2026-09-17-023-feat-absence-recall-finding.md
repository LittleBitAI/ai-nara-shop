---
scope: project
severity: contract
triggers: ["기억", "memory", "회상", "mem0", "저장소.{0,4}기억"]
domain: memory
title: "feat: show the absence items are suppressed by the joint prompt, not unknown to the model"
pr: 23
merged: 2026-09-17
branch: "feat/absence-recall-finding"
---

# feat: show the absence items are suppressed by the joint prompt, not unknown to the model

무엇. 진단 도구의 첫 실제 GPU 회차(408초). v16·v18·v20을 24항목 합동 프롬프트 대신 3항목 별도 스키마로 dev 200건에 물었다.

왜. | 항목 | 지지 | 제출 파이프라인 TP/FP/FN·F1 | 별도 질의 TP/FP/FN·F1 | | --- | ---: | --- | --- | | v16 | 6 | 0 / 0 / 6 · 0.000 | 6 / 139 / 0 · 0.079 | | v18 | 7 | 0 / 0 / 7 · 0.000 | 4 / 109 / 3 · 0.067 | | v20 | 5 | 0 / 0 / 5 · 0.000 | 3 / 109 / 2 · 0.051 | v16은 양성 6건을 전부 잡았다. 6회 연속 TP=0이던 항목이다. 문제의 종류가 바뀐다 — "모델이 못 본다"가 아니라 "모델은 보는데 출력 형식이 0으로 만든다"이고, 남은 일은 미탐 복구가 아니라 정밀도다. …

출처. PR #23 · `feat/absence-recall-finding`
