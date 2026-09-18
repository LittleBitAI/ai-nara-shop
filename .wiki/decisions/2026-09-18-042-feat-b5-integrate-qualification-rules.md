---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: 참가자격 규칙 네 개를 운영 코드에 통합한다 (B5)"
pr: 42
merged: 2026-09-18
branch: "feat/b5-integrate-qualification-rules"
---

# feat: 참가자격 규칙 네 개를 운영 코드에 통합한다 (B5)

무엇. D의 `experiments/qualification_candidate.py`에 있던 v8·v7·v4 올림과 v3 내림을 `script.py` `postprocess`의 ⑤단계로 옮긴다(⑤가 ①~④보다 먼저 돈다). 후보 모듈은 그대로 두고 규칙 본문만 바이트 그대로 복사했다. 이름 충돌은 둘뿐이었다 — `ITEMS` → `QUALIFICATION_ITEMS`, `apply` → `apply_qualification_rules`. 제출 ZIP은 `script. …

왜. (PR 본문에 이유 절이 없다. 이 결정의 근거는 기록되지 않았다)

출처. PR #42 · `feat/b5-integrate-qualification-rules`
