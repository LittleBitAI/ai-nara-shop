---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: PR #35 리뷰의 MEDIUM 2건 — 부재 근거문구 상한과 후보의 script 결합"
pr: 37
merged: 2026-09-18
branch: "fix/c-absence-schema-and-script-binding"
---

# fix: PR #35 리뷰의 MEDIUM 2건 — 부재 근거문구 상한과 후보의 script 결합

무엇. #35 가 리뷰 코멘트 39초 뒤에 머지돼서, 지적한 6건이 그대로 main 에 올라갔다. 그중 실제 실행에 영향을 주는 MEDIUM 2건만 여기서 고친다. LOW 4건은 손대지 않았다.

왜. `reports/team-c/c3-amount-gate/round1-unlock-absence-evidence.diff` 회차 ① diff 가 24항목 전부의 근거문구를 `maxLength: EVIDENCE_MAX`(500)로 열어 주는데, 같은 diff 의 프롬프트 규칙 3 은 부재 항목을 위반여부=1 로 판정하면 인용하라고 적극적으로 지시한다. 부재는 5항목이다. - `MAX_TOKENS` = 2048 - 보관 회차의 실측 최대 출력 = 1055 토큰 (p95 869) → 여유 약 1000 토큰 - diagnose 회차는 200건 중 139건을 v16 양성으로 표시했다 부재 3~5개를 상한 근처로 인용하는 공고 하나면 2048 을 넘긴다. …

출처. PR #37 · `fix/c-absence-schema-and-script-binding`
