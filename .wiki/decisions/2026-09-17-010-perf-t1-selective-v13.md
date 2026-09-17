---
scope: project
severity: preference
triggers: []
domain: ''
title: "perf: recheck only baseline-positive v13 notices"
pr: 10
merged: 2026-09-17
branch: "perf/t1-selective-v13"
---

# perf: recheck only baseline-positive v13 notices

무엇. 전건 v10·v11·v13 추가 분석이 최신 dev 실행에서 330.8초를 썼지만 v10·v11 판정은 하나도 바꾸지 않았습니다. 이제 기본 v13 양성 공고만 v13을 재검증하며 관련 없는 지시·직접생산 조문·중복 인용 생성을 줄입니다.

왜. 기본 24항목 추론·실패 복구와 다른 23항목을 보존합니다. 추가 분석 실패는 동일 공고의 검증된 기본 판정을 유지합니다. Colab은 선택/생략/성공/실패 건수와 실제 기본 CSV의 선택 수를 대조합니다. 검증: 로컬 27개 검사, 비연속 실패 인덱스 추가 검사, Ruff, ZIP 압축 해제 mock 10건·49열 통과. 최신 기록에서는 추가 호출 대상 200→107건, 같은 로컬 토크나이저의 추가 입력 토큰 2,030,736→965,553이며 저장 응답 재조합은 기존 최종 CSV와 일치합니다. 새 프롬프트의 실제 GPU 시간·점수 및 서버 성공은 미검증입니다. 자세한 증거는 reports/t1-baseline/selective-v13.md에 기록했습니다. 사용자 지시로 별도 독립 리뷰를 생략합니다. …

출처. PR #10 · `perf/t1-selective-v13`
