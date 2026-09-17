---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: give the team a run comparison tool and refresh the stale handoff"
pr: 21
merged: 2026-09-17
branch: "feat/compare-runs-and-handoff"
---

# feat: give the team a run comparison tool and refresh the stale handoff

무엇. `docs/tasks/team-handoff.md` 359줄, 기준 커밋 `693c695`. 오늘 확인한 것이 0줄 반영돼 있었다. 기판을 닦아 놓고 안 알려주면 안 닦은 것과 같다.

왜. §0을 신설해 네 가지 실측을 맨 앞에 뒀다: | 확인한 것 | 수치 | | --- | --- | | 서버 첫 채점 | `654c556` 리더보드 0.2197036943 (dev 0.2207877113) | | 시간 여유 14% | 6,192초 / 7,200초 = 86.0%, 여유 1,008초, L40S 1장 | | 회차 간 흔들림 | 같은 조건 두 회차에서 Macro F1 0.0025, v 셀 25/4,800 | | `36b6cc1` 실측 | dev 0.2182553450, 추가 추론 330.8→110.7초, 미제출 | §1(점수), §10(ZIP 전달 → `git pull`), §12(검사 명령 + 회차 후 3단계), 공통 지시문도 고쳤다. …

출처. PR #21 · `feat/compare-runs-and-handoff`
