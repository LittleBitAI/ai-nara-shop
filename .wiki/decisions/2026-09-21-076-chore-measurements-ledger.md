---
scope: project
severity: preference
triggers: []
domain: ''
title: "chore: 측정 추이 장부와 a5-scope 회차를 기록한다"
pr: 76
merged: 2026-09-21
branch: "chore/measurements-ledger"
---

# chore: 측정 추이 장부와 a5-scope 회차를 기록한다

무엇. 측정이 세 곳에 흩어져 추이가 안 보였습니다.

왜. | 어디 | 무엇만 | 빠진 것 | | --- | --- | --- | | `docs/runs.md` 색인 | 회차당 한 줄 | CPU 재생, 파일럿의 네 측정 | | `reports/submissions.json` | 서버 채점만 | dev 측정 전부 | | (없음) | — | CPU 재생 후보들 | `reports/measurements.json`이 이제 모든 측정의 원본입니다. 29행. ``` gpu-run 17 · gpu-pilot 4 · cpu-replay 4 · server 4 2026-09-17 gpu-run 654c556 0.220788 ← 시작 2026-09-18 server 57761ff 0.297862 2026-09-20 gpu-run 18f07e5 0. …

출처. PR #76 · `chore/measurements-ledger`
