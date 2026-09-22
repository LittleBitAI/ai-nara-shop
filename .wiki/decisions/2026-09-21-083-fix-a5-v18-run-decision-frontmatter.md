---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: 회차 등록 결정 문서 front matter + A8 v20 별표 주입 착수서"
pr: 83
merged: 2026-09-21
branch: "fix/a5-v18-run-decision-frontmatter"
---

# fix: 회차 등록 결정 문서 front matter + A8 v20 별표 주입 착수서

무엇. A5 v18 회차 결정 문서 두 건에 front matter를 추가하고, A8 v20 조문 주입 착수서를 작업 큐와 활성 계획에 연결합니다. 회차 기록 본문과 운영 코드는 유지합니다. A8은 기존 company_size 호출에 제공 지침 제2조와 별표 1 원문만 추가하는 실험입니다. 스키마·소비자·관측 게이트를 유지하고, 같은 ZIP의 control/후보를 순서를 바꿔 두 회차 비교합니다.

왜. 1단계 법령 조회는 PR #81로 완료됐지만 주입 효과는 미측정입니다. 계획 검토에서 다음 전제를 정정했습니다. 934자는 직접 조회 확인값이고 약 623토큰은 글자 수 환산 추정입니다. baseline 초과 0/200 계산은 company 입력의 안전성 증거가 아니므로 실제 토크나이저로 추가 절단과 visible 본문 동일성을 검사합니다. 별표는 20억·40억·80억 하한을 담지만 v20 규칙 전체는 아닙니다. 현재 소비자는 SW 사업 여부·참여제한 안내 인용·완전관측을 확인하며 금액을 직접 비교하지 않습니다. 고정 H4 혼합 비교에서 미탐 세 건은 실제 문서 누락으로 막혀 TP 상한이 2입니다. TP≥3을 강제하지 않고 두 회차의 TP/FP 개선·대상 밖 회귀를 확인합니다. …

출처. PR #83 · `fix/a5-v18-run-decision-frontmatter`
