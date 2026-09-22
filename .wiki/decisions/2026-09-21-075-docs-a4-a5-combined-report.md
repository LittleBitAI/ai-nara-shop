---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: A4·A5 합본 측정과 1차 정리"
pr: 75
merged: 2026-09-21
branch: "docs/a4-a5-combined-report"
---

# docs: A4·A5 합본 측정과 1차 정리

무엇. #72를 닫고 그 산출물을 옮깁니다. #69·#71이 머지되면서 #72가 벤더링했던 astra 후보 사본이 필요 없어졌습니다.

왜. `main` 코드로 같은 재생을 다시 돌려 #72 저장본과 바이트 동일함을 확인했습니다. Macro 0.620382330538도 그대로입니다. | | | | --- | --- | | `experiments/a4_a5_combined_candidate.py` | 두 후보를 재생기의 서로 다른 슬롯에 내보내기만 함. 판정 규칙 0줄 | | `reports/team-c/a4-a5-combined/README.md` | 합본 측정 — 간섭 0, 0.620382 | | `reports/team-c/a4-a5-combined/ROLLUP. …

출처. PR #75 · `docs/a4-a5-combined-report`
