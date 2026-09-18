---
scope: project
severity: contract
triggers: ["대화\\s*(모델|프롬프트|응답|생성)", "응답\\s*(정책|수리|스키마)", "페르소나", "말투", "gemini", "openai"]
domain: dialogue
title: "docs: record the 33-notice result and open the prompt experiment as its own ticket"
pr: 32
merged: 2026-09-18
branch: "docs/a-label-result"
---

# docs: record the 33-notice result and open the prompt experiment as its own ticket

무엇. `docs/tasks/label-compare.md` — Opus 5 50건 실행의 실측 기록. 33건 완료·17건 CLI 세션 한도, 건당 179초, Macro F1 0.6205(부분집합이라 dev 0.2208과 비교 금지), 항목별 분포, 기각된 가설. `docs/tasks/prompt-from-labels.md` — 새 티켓. 33건 근거로 Gemma 프롬프트의 v8·v14·v15 질문을 고치고 효과를 재는 실험. 대상 항목·측정 설계·채택 반려 조건. …

왜. Opus 5가 Gemma와 같은 공고·같은 법령 스냅샷·같은 항목 정의를 받고 다른 답을 냈다. | 묶음 | TP | FN | FP | | --- | ---: | ---: | ---: | | Gemma가 6회 내내 TP=0이던 11항목 | 21 | 14 | 4 | | 나머지 13항목 | 31 | 7 | 22 | v8 3/3, v14 5/5, v15 3/3 — 전부 맞혔다. 따라서 **그 항목들의 TP=0은 항목 난이도가 아니라 제출 파이프라인의 결함이다.** 무라벨 공고는 이 구분을 못 해준다. 정답이 없으면 Gemma가 틀린 것인지 원래 답이 0인지 알 수 없다. 프롬프트 실험을 따로 뗀 이유: 그 실험이 곧 라벨링 트랙 전체의 투자 회수 측정이다. …

출처. PR #32 · `docs/a-label-result`
