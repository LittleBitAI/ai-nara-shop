---
scope: project
severity: contract
triggers: ["대화\\s*(모델|프롬프트|응답|생성)", "응답\\s*(정책|수리|스키마)", "페르소나", "말투", "gemini", "openai"]
domain: dialogue
title: "fix: 전체 프롬프트 회귀 철회 및 3항목 별도 판정"
pr: 5
merged: 2026-09-17
branch: "fix/codex-isolate-sme-judgments"
---

# fix: 전체 프롬프트 회귀 철회 및 3항목 별도 판정

무엇. 전체 프롬프트 법령 주입 후보의 dev F1이 0.2208에서 0.1847로 하락하여 기본 24항목 프롬프트를 복원합니다. 같은 모델에서 v10·v11·v13만 별도 판정하고, 나머지 21항목과 근거는 보존합니다. 기존 응답 분할 복구는 유지합니다.

왜. 기본/최종 CSV를 동일 실행에서 채점합니다. Colab은 두 단계 성공·비대상 셀 일치를 확인하고, 같은 실행 기본 F1보다 높으면서 과거 기준선 이상일 때만 제출 ZIP을 자동 다운로드합니다. 검증: 로컬 21개 검사, dev 200건 기본 메시지 1c64604와 완전 일치, 고정 토크나이저 별도 프롬프트 예산, 압축 해제 mock·Ruff·nbformat·UTF-8/LF·diff 검사 통과. 새 후보의 실제 GPU 점수·시간과 서버 성공은 미검증입니다. 사용자 지시로 독립 리뷰를 생략합니다.

출처. PR #5 · `fix/codex-isolate-sme-judgments`
