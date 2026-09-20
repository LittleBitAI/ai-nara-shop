---
scope: project
severity: preference
triggers: []
domain: ''
title: "A3 H3: 요건 상태 대신 본문 조항을 관측"
pr: 63
merged: 2026-09-20
branch: "feat/a3-observed-clauses"
---

# A3 H3: 요건 상태 대신 본문 조항을 관측

무엇. A3 회차 3의 H2는 v18 첫 TP 1건을 얻었지만 v10·v20 TP는 0이었다. 기존 company_size 호출에서 직접생산/SW 참여제한의 상태 필드 두 개를 제거하고, 본문 조항 원문 또는 null로 관측을 답하게 한다. 기존 적용 대상·원문 인용·완전관측 조건을 통과한 경우에만 null을 부재로 연결한다. SW 적용 대상 인용은 120자 이내의 연속 원문으로 제한한다. …

왜. H2에서 competitive 74건 중 not_required가 15건이었고, software_business=yes 10건 중 software_participation=unknown이 9건이었다. 문서의 조항 존재와 법적 필요 여부를 상태 하나로 묻게 한 설계를 분리한다. 과거 unknown/not_required를 부재로 재해석하지 않도록 스키마 버전을 실행 설정에 기록한다. 여러 품목표 행을 합친 SW 인용이 원문 검증에 실패한 문제도 짧은 연속 인용으로 다룬다.

출처. PR #63 · `feat/a3-observed-clauses`
