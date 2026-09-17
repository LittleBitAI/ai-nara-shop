---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: 품목 적용 범위와 참가자격 판정 보완"
pr: 6
merged: 2026-09-17
branch: "fix/codex-sme-applicability"
---

# fix: 품목 적용 범위와 참가자격 판정 보완

무엇. 기존 v10·v11·v13 별도 판정은 품목명 일치를 적용 확정으로 오인하고, 정식 품명이 없는 서비스의 고시 후보를 놓쳤다. 코드/문자열 일치 출처와 고시 미등재 코드를 구분하고, 코드가 일치하지 않는 용역에는 제공 서비스 목록을 함께 전달한다. 판정 지시는 품목 특이사항·계약 예외·실제 참가자격을 확인하며 중·소기업과 소기업만 허용하는 조건을 구분한다.

왜. 기본 24항목 메시지·모델 설정·분할 재시도와 다른 21항목 보존 구조, Colab 품질 기준은 유지한다. 이전 실제 결과 분석과 새 후보의 검증 범위는 reports/t1-baseline/sme-applicability.md에 기록했다. 검증: baseline 13개, package/Colab 5개, score 4개 통과. 기본 dev 메시지 200건 동일, 고정 리비전 FastTokenizer 최대 14,261토큰·추가 문서 축소 0건. ZIP 압축 해제 mock, Ruff, UTF-8 without BOM/LF, 링크, diff 검사 통과. 새 후보의 실제 GPU 실행·F1·시간·서버 성공은 미검증이다. 사용자가 Colab에서 실제 후보를 재실행해야 한다. …

출처. PR #6 · `fix/codex-sme-applicability`
