---
scope: project
severity: contract
triggers: ["대화\\s*(모델|프롬프트|응답|생성)", "응답\\s*(정책|수리|스키마)", "페르소나", "말투", "gemini", "openai"]
domain: dialogue
title: "fix: accept equivalent binary judgments and ignore extra fields"
pr: 9
merged: 2026-09-17
branch: "fix/t1-tolerant-response"
---

# fix: accept equivalent binary judgments and ignore extra fields

무엇. 모델이 뜻이 같은 이진값이나 추가 설명 필드를 반환해도 기존 검사가 응답을 거부해 재시도·전체 중단으로 이어질 수 있었다. 명확한 bool/숫자/문자열 이진값은 정수 0/1로 정규화하고 추가 필드만 버린다.

왜. 필수 판정이나 facts가 없거나 값이 모호하면 기존 분할 복구를 유지한다. 정상 응답 없는 공고를 0으로 채우지 않는다. 프롬프트·입력 예산·점수 조건·CSV 계약은 유지한다. 검증: 청크 62의 기본/추가 단계 16조합에서 수정 전 실패, 수정 후 불필요한 재호출 없이 통과. baseline 17 + package 5 + score 4 검사, Ruff/diff/UTF-8/LF, ZIP mock 검증 통과. dev 200건 프롬프트와 정상 JSON 파싱 결과 동일성 확인. 팀원 성공 제출본은 제공 baseline과 동일하며 최초 서버 오류를 유발한 실제 응답 종류는 미확정이다. 새 후보의 실제 GPU/서버 성공·점수 개선은 미검증. 독립 리뷰는 사용자 지시로 생략한다.

출처. PR #9 · `fix/t1-tolerant-response`
