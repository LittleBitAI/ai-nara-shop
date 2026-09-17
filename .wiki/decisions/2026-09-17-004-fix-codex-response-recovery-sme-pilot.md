---
scope: project
severity: contract
triggers: ["대화\\s*(모델|프롬프트|응답|생성)", "응답\\s*(정책|수리|스키마)", "페르소나", "말투", "gemini", "openai"]
domain: dialogue
title: "fix: 응답 분할 복구 및 경쟁제품 판정 파일럿"
pr: 4
merged: 2026-09-17
branch: "fix/codex-response-recovery-sme-pilot"
---

# fix: 응답 분할 복구 및 경쟁제품 판정 파일럿

무엇. 실패한 24항목 응답을 같은 조건으로 반복하던 경로를, 해당 공고의 6항목씩 분할 재생성으로 바꿉니다. 각 그룹과 최종 24항목을 모두 검증하며, 복구 실패를 정상 CSV로 처리하지 않습니다.

왜. 성능 파일럿으로 v10·v11·v13에 제공 판로지원법 조항·예외와 고시 품목 조회 결과를 전달합니다. Colab은 제공 자산 해시와 동일 dev 기준선(F1 0.2208013652894021) 대비 지표를 기록합니다. 검증: 로컬 20개 검사, 고정 토크나이저 dev 200건 예산 검사, 실제 후보 커밋 clone/패키징, Ruff·nbformat·UTF-8/LF·diff 검사 통과. 새 후보의 실제 GPU 복구·F1 개선 및 최초 서버 오류 해결은 미검증이며 Colab 재실행이 필요합니다. 사용자 지시로 독립 리뷰를 생략합니다.

출처. PR #4 · `fix/codex-response-recovery-sme-pilot`
