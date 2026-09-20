---
scope: project
severity: preference
triggers: []
domain: ''
title: "exp: 추가 호출 세 실험을 main 하나로 합치고 상수로 켜고 끈다"
pr: 54
merged: 2026-09-18
branch: "exp/integrate-extra-calls"
---

# exp: 추가 호출 세 실험을 main 하나로 합치고 상수로 켜고 끈다

무엇. 브랜치 5개를 1개로 줄인다. 실험 셋(`exp/n1-absence-split`·`exp/n2-amount-band`·`exp/n3-competitive-product`)이 각자 살아 있으면 다음 회차마다 어느 브랜치를 가리킬지 정해야 하고, 셋을 같이 쓸 수도 없다.

왜. 셋 다 합동 24항목 호출 뒤에 더하기만 하는 독립 단계라 한 파일에 공존할 수 있다. 각자 최상위 항목 리스트 하나로 켜고 끈다 — 빈 리스트면 그 단계가 통째로 안 돈다. ```python SPLIT_ITEMS = ["v16", "v18"] # N1 — 켜짐 BAND_ITEMS = [] # N2 — 회차 미실행, 꺼짐 PRODUCT_ITEMS = [] # N3 — 시간이 막아 꺼짐 ``` 각 회차가 자기 `baseline_submission.csv` 를 같이 담고 있다. 같은 모델 출력이라 churn 이 섞이지 않는다. 회차 간 절대 Macro 비교는 쓰지 않는다 — 같은 코드가 dev 0.2182 를 세 번, 0.2208 을 한 번 냈다. …

출처. PR #54 · `exp/integrate-extra-calls`
