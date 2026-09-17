---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: ask the model which step blocked a zero-score item"
pr: 18
merged: 2026-09-17
branch: "feat/item-diagnosis"
---

# feat: ask the model which step blocked a zero-score item

무엇. 0점 항목이 문맥 관측 → 사실 추출 → 조건 비교 → 후처리 중 어디서 막혔는지 볼 계기를 놓는다. 점수 개선 자체는 담당자 몫이고, 이 변경은 제출 판정을 바꾸지 않는다 — `git diff script.py`는 비어 있다.

왜. 제출물 `script.py`를 import만 해 `iter_records`·`item_table`·`build_messages`·`fit_to_budget`·`VLLMRunner`를 재사용한다. `SME_ITEMS`·`submission.csv`는 그대로다. 별도 스키마로 항목마다 네 칸을 받는다: ```json {"id": "PPS-DEV-20", "items": {"v16": {"요구사항": "...", "공고_인용": "...", "판정": 0, "막힌_단계": "condition_not_met"}}, "truth": {"v16": 1}, "budget": {"prompt_tokens": 8774}} ``` `막힌_단계`는 `.wiki/plan-active.md`의 네 단계와 같은 이름이다 …

출처. PR #18 · `feat/item-diagnosis`
