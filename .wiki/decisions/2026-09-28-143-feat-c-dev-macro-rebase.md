---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: PR #143 을 방안 (가) 로 되살린다 — main 을 들이고, 세 규칙을 3c36bba 위에서 다시 재고, 문서·검사를 맞춘다"
pr: 143
merged: 2026-09-28
branch: "feat/c-dev-macro-rebase"
---

# fix: PR #143 을 방안 (가) 로 되살린다 — main 을 들이고, 세 규칙을 3c36bba 위에서 다시 재고, 문서·검사를 맞춘다

무엇. 이 PR 은 159 커밋 뒤처져 있었다. 방안 (가) 로 되살린다 — rebase 하지 않고 `main` 을 들이고, 세 규칙을 현재 기준선 위에서 다시 재고, 문서와 검사를 거기에 맞춘다. `script.py` 는 이 PR 에서 안 건드린다.

왜. 브랜치가 `main` 보다 159 커밋 뒤였다. 검사 파일이 50개뿐이고 `main` 에만 있는 일곱(`test_c11_competition_exception` · `test_c9_catalogue_exclusion` · `test_c_variance_aggregate` · `test_clause_rules` · `test_facts_exception` · `test_luna_api` · `test_v1_verdict`)이 없었다. - `c6-integrated.diff` 가 현재 `main` 에 안 붙는다(`script.py:736` 에서 실패). - `RUN-REQUEST.md` §3 의 회차 브랜치 블록이 명령처럼 적혀 있었다 — 열린 [P2]. - `README. …

출처. PR #143 · `feat/c-dev-macro-rebase`
