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

What. Misses the opportunity to see where a zero-score item was blocked among context observation → fact extraction → condition comparison → post-processing. Score improvement itself is the responsibility of the person in charge, and this change does not alter the submission judgment — `git diff script.py` is empty.

Why. Only imports submission `script.py` to reuse `iter_records`·`item_table`·`build_messages`·`fit_to_budget`·`VLLMRunner`. `SME_ITEMS`·`submission.csv` remain the same. Receives four slots for each item via a separate schema: ```json {"id": "PPS-DEV-20", "items": {"v16": {"요구사항": "...", "공고_인용": "...", "판정": 0, "막힌_단계": "condition_not_met"}}, "truth": {"v16": 1}, "budget": {"prompt_tokens": 8774}} ``` `막힌_단계` has the same names as the four steps of `.wiki/plan-active.md` …

Source. PR #18 · `feat/item-diagnosis`
