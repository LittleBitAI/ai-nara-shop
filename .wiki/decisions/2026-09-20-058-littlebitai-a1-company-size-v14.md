---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: 기업규모 결정표로 v14·v15·v16에 첫 TP를 세운다 (A1)"
pr: 58
merged: 2026-09-20
branch: "LittleBitAI/a1-company-size-v14"
---

# feat: 기업규모 결정표로 v14·v15·v16에 첫 TP를 세운다 (A1)

무엇. 작업은 `merganser` 워크트리의 astra 세션이 했고, 회차 등록·측정·이 본문은 주 작업공간에서 했다. 티켓은 `docs/tasks/a1-company-size.md`, 설계 근거는 `reports/team-c/a1-company-size/result.md`가 소유한다. 참가자격의 기업 등급을 한 번 추출하고 금액 구간 비교를 코드로 하는 `company_size` 단계를 붙였다. 여섯 회차 내내 0이던 세 항목이 섰다. …

왜. 금액 구간은 이미 정답과 100% 일치했다. dev 200건 전부 가격이 있고 v14 양성 8건이 전부 고시금액 이상, v15 6건이 전부 1억~고시, v17 6건이 전부 1억 미만이다. 그런데 금액 게이트만 추가하는 후처리는 실측 +0.0001이었다 — 모델이 이미 구간 안에서만 발화하기 때문이다 (v17 예측 40건 중 39건). 가로축은 문제가 아니었다. 문제는 세로축이었고 모델 출력에 그 신호가 없었다. 정답 v14 양성 8건에서 모델이 v13~v18 중 하나도 발화하지 않았다. 없는 신호는 후처리로 못 살리므로 호출 구조를 바꾸는 수밖에 없었다. …

출처. PR #58 · `LittleBitAI/a1-company-size-v14`
