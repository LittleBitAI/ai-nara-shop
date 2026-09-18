---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: lower v9/v19/v21/v24 positives whose own evidence refutes the item"
pr: 30
merged: 2026-09-18
branch: "feat/b-evidence-rules"
---

# feat: lower v9/v19/v21/v24 positives whose own evidence refutes the item

무엇. `script.py` `postprocess`에 ④단계 `evidence_refutes()`를 넣었다. 모델이 인용한 근거가 그 항목의 위반 조건을 스스로 부정하면 양성을 0으로 내린다. - v19: 근거에 계약 시·계약체결·낙찰자 결정이 있고 `입찰`·`투찰`이 없는 경우 - v24: 근거의 금액·지역제한·(계약방법·금액구간)이 같은 뜻의 메타 필드와 전부 일치하는 경우 - v21: 지분율이 모두 10% 이상이거나, 수치 없이 공동계약 불허 문구인 경우 - v …

왜. 담당 4항목(v9·v19·v21·v24)의 FP가 114건(이 회차 기준)으로 전체 오탐의 대부분을 차지했다. 보관 원응답 재생(`colab-1789655036303880754/dev-debug`)으로 측정했다. 후보와 기준이 같은 모델 출력을 쓰므로 회차 간 churn이 없다. | 항목 | TP | FP | F1 | | --- | --- | --- | --- | | v19 | 6→6 | 21→16 | 0.3636→0.4286 | | v24 | 4→4 | 43→33 | 0.1455→0.1778 | | v21 | 4→4 | 34→9 | 0.1818→0.4211 | | v9 | 5→5 | 16→11 | 0.3704→0.4545 | 대상 밖 변화는 0셀이다. dev Macro F1은 0.2182→0.2357이다. …

출처. PR #30 · `feat/b-evidence-rules`
