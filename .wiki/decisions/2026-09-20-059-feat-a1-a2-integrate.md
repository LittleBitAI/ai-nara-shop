---
scope: project
severity: preference
triggers: []
domain: ''
title: "Merge: A1 기업규모 결정표와 A2 경쟁제품 규칙을 합친다"
pr: 59
merged: 2026-09-20
branch: "feat/a1-a2-integrate"
---

# Merge: A1 기업규모 결정표와 A2 경쟁제품 규칙을 합친다

무엇. #57(A2)과 #58(A1)을 합쳤다. **base가 `feat/a2-competitive-product`라 이 PR의 diff는 A1 머지분과 통합에서 생긴 수리만 보인다.** #57이 머지되면 GitHub이 base를 `main`으로 옮긴다. A1 회차의 보관 원응답으로 합본을 GPU 0초에 쟀다. A2가 순수 후처리라 가능했다. ``` Macro F1 0.434621 → 0.469806 (+0. …

왜. 두 후보가 서로 다른 항목을 보고 A2가 순수 후처리라 간섭이 없다. 합치지 않을 이유가 없었다. ### 충돌 아홉 개를 A1 쪽으로 풀었다 astra와 내가 무라벨 규칙·`DRIFT_MAX`·재생·노트북을 각자 고쳤는데 결론이 같았다. A1은 GPU로 검증된 구조이므로 그쪽을 취하고 A2 코드 94줄을 그 위에 얹는 것이 가장 짧고 안전한 통합이다. ### 다만 그 선택이 재생 결함을 되살렸다 A1의 `replay_run`도 `baseline`·`sme`·`company_size`만 읽어 `split`·`product` 원응답을 무시한다. #57의 `0cf061f`가 고친 바로 그 결함이다. …

출처. PR #59 · `feat/a1-a2-integrate`
