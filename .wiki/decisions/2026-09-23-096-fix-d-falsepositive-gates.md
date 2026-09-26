---
scope: project
severity: contract
triggers: ["대화\\s*(모델|프롬프트|응답|생성)", "응답\\s*(정책|수리|스키마)", "페르소나", "말투", "gemini", "openai"]
domain: dialogue
title: "fix: Remove 6 false positives with v3·v5·v6 scope gate (v4 withdrawal · v2 prompt axis refutation record)"
pr: 96
merged: 2026-09-23
branch: "fix/d-falsepositive-gates"
---

# fix: Remove 6 false positives with v3·v5·v6 scope gate (v4 withdrawal · v2 prompt axis refutation record)

What. There are two commits. They are independent, so you can read them separately. ① `f11b14e` — v3·v4·v5·v6 scope gate. `script.py` Only post-processing is changed. Prompt·schema·inference path·dependency changes 0. | Item | Pre TP/FP/FN | Post TP/FP/FN | F1 | Individual contribution | | --- | --- | --- | --- | ---: | | v3 performance limit 1x or more | 8 / 4 / 0 | 8 / 0 / 0 | 0.800000 → 1.000000 | +0. …

Why. ### ① All four were wiring issues v3 — The old code used `실적` as an anchor to pick the maximum amount in the entire document. `PPS-DEV-03` picked up 100 million won (1.12x) in the main text and kept a citation requiring 30 million won (0.34x), and `PPS-DEV-25` missed the anchor entirely because `실적` was 0 times in the main text. Now it only reads within the evidence phrase. It also reads ratio notation — since the provision allows `해당 계약목적물의 추정가격의 1배 이내` (National/Local enforcement Rule Article 25, Paragraph 2, Subparagraph 1, Item B), `예산금액의 100% 이상` is not a violation. It is not a threshold chosen by looking at dev, but 1x of the provision. v4 — `detect_institution_performance()` was registered in `RULES` and was already running in every announcement. …

Source. PR #96 · `fix/d-falsepositive-gates`
