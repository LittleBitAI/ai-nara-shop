---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: 회차 변동폭을 쟀다 — 같은 코드 6회의 Macro 범위는 0.007287"
pr: 152
merged: 2026-09-27
branch: "run/c-variance"
---

# feat: 회차 변동폭을 쟀다 — 같은 코드 6회의 Macro 범위는 0.007287

무엇. C 파트의 회차 기록·후보·감사를 모은다. 운영 코드(`script.py`·`tools/`·`notebooks/`)는 merge-base 대비 diff 가 비어 있다. | 무엇 | 상태 | | --- | --- | | 회차 변동폭 N=6 (`colab-1790445336782946136`) | 돌았다. 같은 코드 여섯 통과의 dev Macro 관측 범위 `0.007287157287`, 쌍별 갈린 셀 0~2. 서버 변동폭이 아니다 …

왜. 9/25 의 0.034 가 무엇인지 확정해야 팀의 판정이 분모를 가진다. 여섯 통과로 같은 코드의 dev 관측 범위를 쟀고, 그 범위보다 작은 후보는 회차가 아니라 같은 원응답 위 재생으로만 가른다. C11 은 그렇게 가른, GPU 없이 v10 오탐을 닫는 후보다.

출처. PR #152 · `run/c-variance`
