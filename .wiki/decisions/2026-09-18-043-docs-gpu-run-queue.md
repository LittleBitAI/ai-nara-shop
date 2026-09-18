---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: GPU 회차 12번을 어디에 쓸지 대기열로 적는다"
pr: 43
merged: 2026-09-18
branch: "docs/gpu-run-queue"
---

# docs: GPU 회차 12번을 어디에 쓸지 대기열로 적는다

무엇. `docs/tasks/gpu-run-queue.md` 신설, `docs/README.md` 문서 지도에 한 행. 문서만 바뀐다.

왜. GPU 회차 12번을 쓸 수 있게 됐다. 그런데 병목 셋은 그대로다. | 자원 | 남은 것 | 회차가 늘면 풀리나 | | --- | --- | --- | | GPU 회차 | 12회 | — | | 대회 제출 | 하루 1회 · 약 11회 | 아니오 | | 서버 실행 시간 | 여유 1,008초 | 아니오 | | 라벨 | dev 200건이 전부 | 아니오 | 그래서 회차는 *가설을 가르는 데* 쓰고 일반화는 *매일 제출로* 쌓는다.

출처. PR #43 · `docs/gpu-run-queue`
