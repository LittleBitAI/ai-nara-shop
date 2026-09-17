---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: 4인 점수 개선 계획과 현재 계획 위키 연결"
pr: 11
merged: 2026-09-17
branch: "docs/team-score-plan"
---

# docs: 4인 점수 개선 계획과 현재 계획 위키 연결

무엇. 현재 dev Macro F1 0.2208과 6회 실행 기록을 바탕으로 4인 팀의 1주 0.60 도전 계획을 정리합니다. 24항목 담당, 19개 티켓, 첫 48시간 C3(v16/v18)·D1(v8)의 TP 회복 기준과 Opus 전달 지시문을 제공합니다. 목표 점수와 실제 달성 수치는 구분하며 기존 서버 실패 복구를 보호합니다.

왜. 프로젝트 위키의 현재 계획 요약과 문서 진입점을 갱신했습니다. 현재 계획·팀원 업무·다음 작업 질문과 SessionStart 직접 실행에서 목표·우선 작업·상세 문서가 주입됨을 확인했습니다. 검증: 실제 6회 CSV 재채점 일치, 24항목 배정·19개 티켓·사례 원문 12곳 대조, 11개 파일 UTF-8/LF·68개 로컬 링크·JSON 파싱·diff 검사, 위키 sync·repo_lint 통과. 직접 주입 기록은 reports/team-score-audit/wiki-checks.json에 있습니다. 문서 변경이며 새 모델 추론·서버 제출·팀원 PC 검증은 수행하지 않았습니다. 사용자 요청에 따라 별도 리뷰 없이 머지합니다.

출처. PR #11 · `docs/team-score-plan`
