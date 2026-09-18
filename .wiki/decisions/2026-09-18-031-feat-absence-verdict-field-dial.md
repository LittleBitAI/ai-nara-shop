---
scope: project
severity: contract
triggers: ["기억", "memory", "회상", "mem0", "저장소.{0,4}기억"]
domain: memory
title: "feat: show the absence recall swings 4x with how the verdict is asked"
pr: 31
merged: 2026-09-18
branch: "feat/absence-verdict-field-dial"
---

# feat: show the absence recall swings 4x with how the verdict is asked

무엇. 진단 도구의 판정 칸을 하나로 합친 뒤 첫 GPU 회차를 등록한다. 어긋남은 사라졌지만 부재탐지 재현율이 13/18에서 3/18로 떨어졌다. `reports/team-score-audit/absence-detection.md`를 두 회차 대조로 다시 쓰고, 같은 `script.py`의 다섯 번째 측정으로 churn 관측을 열두 쌍으로 늘린다.

왜. ### 앞 회차의 "v16 6/6"은 모델 실력이 아니었다 같은 모델·같은 공고·같은 항목인데 판정을 묻는 방식을 바꿨다. | | 느슨 — 별도 `판정` 칸 (`…172468461`) | 보수 — 칸 제거+보수화 지시 (`…726180378`) | | --- | --- | --- | | v16 (지지 6) | 6 / 139 / 0 · F1 0.079 | 1 / 29 / 5 · F1 0.056 | | v18 (지지 7) | 4 / 109 / 3 · F1 0.067 | 2 / 34 / 5 · F1 0.093 | | v20 (지지 5) | 3 / 109 / 2 · F1 0.051 | 0 / 0 / 5 · F1 0. …

출처. PR #31 · `feat/absence-verdict-field-dial`
