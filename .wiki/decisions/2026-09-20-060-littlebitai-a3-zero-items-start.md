---
scope: project
severity: preference
triggers: []
domain: ''
title: "A3: 기업규모 추출의 원천·문장 역할 구분과 고정 Colab 실행"
pr: 60
merged: 2026-09-20
branch: "LittleBitAI/a3-zero-items-start"
---

# A3: 기업규모 추출의 원천·문장 역할 구분과 고정 Colab 실행

무엇. 기업규모 추출의 qualification 프롬프트에서 공고문 자격, 제출서류 목록, 법령 인용·참여 배제, 나라장터 메타를 구별하도록 수정합니다. 스키마·scope·결정표·후처리·호출 수는 유지합니다. A3 전용 Colab 노트북 `notebooks/exp-a3-source-role.ipynb`는 추론 후보 `b7ac2650eccd0d8a6ae41919260b158987fd30ff`를 clone하도록 고정합니다. …

왜. scope 회차 원응답에서 v18 양성 7건 중 4건이 공고문 대신 meta.조항호내용을 자격 근거로 그대로 복사했습니다. 전체 dev에서는 같은 현상이 8건입니다. 공고 ID별 예외 없이 문서 원천과 문장 역할을 먼저 읽는 단일 가설을 실제 모델에서 검증하려는 후보입니다.

출처. PR #60 · `LittleBitAI/a3-zero-items-start`
