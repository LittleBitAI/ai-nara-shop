---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: 규칙의 낱말을 어디서 찾나 — 신뢰 항목 목록이 문서에 없다"
pr: 170
merged: 2026-09-28
branch: "docs/rule-lookup-index"
---

# docs: 규칙의 낱말을 어디서 찾나 — 신뢰 항목 목록이 문서에 없다

무엇. "신뢰도·C파트·D파트 규칙을 찾기 어렵다" 는 지적을 받고 실제로 찾아본 결과를 문서 지도에 넣는다. 파일 둘, 추가 70줄(삭제 1줄은 표 한 칸 수정). | 파일 | 무엇 | | --- | --- | | `docs/README.md` | 낱말로 찾는 표 + 항목 집합 상수 열한 곳 | | `reports/team-c/c-fewshot/RUN-REQUEST.md` | §2-2 — 기준 3 이 내 대상을 안 지킨다 |

왜. 문서 지도(`docs/README.md`)는 작업으로 찾게 돼 있다("채점·실험", "패키징·제출" …). 그런데 막히는 자리는 규칙 문장에 나오는 낱말이다 — "신뢰 항목이 순 `(TP − FP)` 1셀 넘게 안 잃는다" 를 읽고 그 신뢰 항목이 무엇인지 찾으려 하면 지도가 안 도와준다.

출처. PR #170 · `docs/rule-lookup-index`
