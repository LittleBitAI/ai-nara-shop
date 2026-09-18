---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: PR #34 리뷰 6건 — 복합 금액, v8 배점표 가드, 절 경계, 낡은 해시"
pr: 39
merged: 2026-09-18
branch: "HyeongyeongKim/d-review-fixes"
---

# fix: PR #34 리뷰 6건 — 복합 금액, v8 배점표 가드, 절 경계, 낡은 해시

무엇. [PR #34](https://github.com/LittleBitAI/ai-nara-shop/pull/34) 리뷰가 낸 6건을 고친다. #34는 그 사이 머지돼서 후속 PR로 올린다.

왜. 1. 복합 금액을 33% 낮게 읽었다. `MONEY`가 `억`과 `천만`을 따로 잡고 `max`를 취해 `1억 5천만원`이 1억으로 읽혔다. 그 값이 1배 경계를 넘나들면 v3 규칙이 정답 양성을 내려 버린다 — 이 규칙이 막으려던 바로 그 실패다. 한 번의 일치로 억·천만·만·원 자리를 모두 먹고 더한다. 자리 표시 없는 맨 숫자는 `원`이 붙었을 때만 금액으로 본다. 그러지 않으면 세부품명번호 10자리와 날짜를 금액으로 읽는다. 이 수정으로 `PPS-DEV-078`의 금액을 읽게 되어 v3 FP가 6에서 5로 더 줄었다. 2. v8 `detect`에 배점표 가드가 없었다. 리뷰가 낸 문장을 그대로 재현했다. …

출처. PR #39 · `HyeongyeongKim/d-review-fixes`
