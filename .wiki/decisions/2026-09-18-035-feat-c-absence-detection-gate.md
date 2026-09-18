---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: gate absence detection by the amount band the 조문 sets"
pr: 35
merged: 2026-09-18
branch: "feat/c-absence-detection-gate"
---

# feat: gate absence detection by the amount band the 조문 sets

무엇. C3·C4·C7 의 CPU 단계 결과다. 모델을 부르지 않았고 제출 CSV 를 만들지 않았다. `script.py` 와 `tools/` 는 건드리지 않았다 — 두 건 다 patch 로만 전달한다. | 파일 | 내용 | | --- | --- | | `experiments/sme_candidate.py` | v16·v18 금액 게이트 `postprocess` 후보. v20 은 넣지 않았다 | | `tests/test_sme_candidate.py` | 18건. …

왜. 별도 질의는 v16 양성 6건을 전부 잡았지만 200건 중 139건을 위반이라 했다. 문제는 미탐이 아니라 정밀도였다. 금액 경계는 분포가 아니라 제공 조문에서 정했다. 고시금액 = 2억 3천만 원 — 재정경제부장관 고시 1.가 (물품 및 용역, WTO 정부조달협정). 국가계약법 시행령 제2조제3호가 이 고시를 가리킨다. 1억 경계 — 국가 시행령 제21조①10호 가목(1억원 미만 → 소기업·소상공인)·나목(1억원 이상 → 중소기업자). 지방도 같은 값 — 지방 시행령 제20조①12호가 행안부 고시가 아니라 국가 고시금액을 명시 참조한다. 인수인계의 잠정값 2.2억은 FP 가 3건 적지만(36 대 39) 제공 조문에 근거가 없어 쓰지 않았다. 수치를 맞추려고 경계를 움직이지 않았다. …

출처. PR #35 · `feat/c-absence-detection-gate`
