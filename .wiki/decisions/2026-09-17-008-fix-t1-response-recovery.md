---
scope: project
severity: contract
triggers: ["대화\\s*(모델|프롬프트|응답|생성)", "응답\\s*(정책|수리|스키마)", "페르소나", "말투", "gemini", "openai"]
domain: dialogue
title: "fix: prevent optional analysis failures from aborting valid submissions"
pr: 8
merged: 2026-09-17
branch: "fix/t1-response-recovery"
---

# fix: prevent optional analysis failures from aborting valid submissions

무엇. 기본 판정의 6항목 재시도가 잘못된 응답을 반환하면 제출 전체가 중단됐다. 실패한 그룹만 단일 항목으로 더 나눠 복구하며, 이미 정상 응답을 받은 그룹은 보존한다.

왜. 추가 3항목 분석 실패는 동일 공고의 검증된 기본 24항목 판정으로 돌아간다. 기본 정상 응답이 없는 공고는 성공 처리하지 않으며, Colab은 추가 성공과 기본 보존 건수를 구분한다. 영어 프롬프트와 점수 임계값은 유지한다. 검증: 수정 전 중단 경로 2개 재현, baseline 16 + package 5 + score 4 검사 통과. 청크 인덱스 62 회귀, 기본 응답/이웃 공고 보존, 허위 성공 거부, ZIP 압축 해제 mock, Ruff/노트북 구문/인코딩 통과. dev 200건의 기본/추가 프롬프트 동일성을 확인했다. 실제 새 GPU/서버 성공은 미검증이다. 이전 Colab에서 출력 잘림 3건을 복구한 증거와 최초 서버 오류의 미확정 원인을 구분했다. …

출처. PR #8 · `fix/t1-response-recovery`
