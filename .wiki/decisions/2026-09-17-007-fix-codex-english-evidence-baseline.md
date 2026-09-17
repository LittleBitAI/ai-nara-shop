---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: 영어 판정 지시와 3항목 사실 검증"
pr: 7
merged: 2026-09-17
branch: "fix/codex-english-evidence-baseline"
---

# feat: 영어 판정 지시와 3항목 사실 검증

무엇. 이전 3항목 보완은 dev F1 0.211008로 같은 실행 기본 판정보다 낮았고, v13에서 중기업을 허용하는 문구도 위반으로 판단했다. 사용자 요청에 따라 기본·별도·재시도 지시를 영어로 바꾸고 한국어 법적 용어·제공 원문은 유지한다.

왜. 별도 단계는 품목 코드·대상 인용·적용 조건·자격 문구·예외를 facts 스키마로 추출한다. 코드는 실제 제공한 고시 후보와 원문 인용, 판정 상태를 대조하고 중기업 포함 자격과 미관측 부재 단정을 거른다. 사실 응답 형식이 깨지면 기존 분할 복구를 사용하며 실패를 정상 0으로 대체하지 않는다. Colab은 영어 기본 판정과 검증 후 판정을 비교한다. 다운로드 조건은 기존 그대로 최종 F1이 같은 실행 기본 F1을 초과하고 0.2208013652894021 이상이어야 한다. 다른 21항목 보존, HF_TOKEN 다운로드, 서버 진입점·고정 설정·ZIP 동일성 검사를 유지한다. 검증: 로컬 baseline 15개, package/Colab 5개, score 4개 통과. …

출처. PR #7 · `fix/codex-english-evidence-baseline`
